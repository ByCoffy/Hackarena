import threading, logging
from flask import request
from flask_login import current_user
from flask_socketio import emit, disconnect
from app import docker_manager
logger = logging.getLogger(__name__)
exec_sessions = {}

def register_terminal_events(socketio):
    @socketio.on('connect', namespace='/terminal')
    def handle_connect():
        if not current_user.is_authenticated: disconnect(); return
        emit('output', {'data': '\r\n\x1b[32m[CTFArena]\x1b[0m Conectando...\r\n'})

    @socketio.on('start_terminal', namespace='/terminal')
    def handle_start_terminal(data):
        if not current_user.is_authenticated: disconnect(); return
        cid = data.get('challenge_id')
        if not cid: emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m No challenge ID.\r\n'}); return
        container = docker_manager.get_container(current_user.id, cid)
        if not container: emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m No hay instancia activa.\r\n'}); return
        try:
            ei = container.client.api.exec_create(container.id, '/bin/bash', stdin=True, tty=True, stdout=True, stderr=True,
                environment={'TERM': 'xterm-256color', 'COLUMNS': str(data.get('cols', 80)), 'LINES': str(data.get('rows', 24))})
            es = container.client.api.exec_start(ei['Id'], socket=True, tty=True)
            sid = request.sid
            exec_sessions[sid] = {'socket': es, 'exec_id': ei['Id'], 'container_id': container.id, 'user_id': current_user.id, 'challenge_id': cid}
            emit('output', {'data': '\r\n\x1b[32m[CTFArena]\x1b[0m Conectado! Buena suerte \xf0\x9f\x9a\xa9\r\n\r\n'})
            threading.Thread(target=_read_output, args=(socketio, sid, es), daemon=True).start()
        except Exception as e:
            logger.error(f"Exec error: {e}")
            emit('output', {'data': f'\r\n\x1b[31m[Error]\x1b[0m {str(e)}\r\n'})

    @socketio.on('input', namespace='/terminal')
    def handle_input(data):
        s = exec_sessions.get(request.sid)
        if not s: return
        try: s['socket']._sock.sendall(data.get('data', '').encode('utf-8'))
        except: emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m Conexion perdida.\r\n'}); _cleanup(request.sid)

    @socketio.on('resize', namespace='/terminal')
    def handle_resize(data):
        s = exec_sessions.get(request.sid)
        if not s: return
        try:
            c = docker_manager.client.containers.get(s['container_id'])
            c.client.api.exec_resize(s['exec_id'], height=data.get('rows', 24), width=data.get('cols', 80))
        except: pass

    @socketio.on('disconnect', namespace='/terminal')
    def handle_disconnect(): _cleanup(request.sid)

def _read_output(socketio, sid, es):
    try:
        while sid in exec_sessions:
            try:
                data = es._sock.recv(4096)
                if not data: break
                socketio.emit('output', {'data': data.decode('utf-8', errors='replace')}, namespace='/terminal', to=sid)
            except (ConnectionResetError, OSError): break
    finally:
        socketio.emit('output', {'data': '\r\n\x1b[33m[CTFArena]\x1b[0m Sesion finalizada.\r\n'}, namespace='/terminal', to=sid)
        _cleanup(sid)

def _cleanup(sid):
    s = exec_sessions.pop(sid, None)
    if s:
        try: s['socket']._sock.close()
        except: pass
