"""
WebSocket Terminal Handler

Connects the browser's xterm.js terminal to a Docker container's shell
via Flask-SocketIO. Each user gets their own isolated exec session.
"""

import docker
import threading
import logging
from flask import request
from flask_login import current_user
from flask_socketio import emit, disconnect
from app import docker_manager

logger = logging.getLogger(__name__)

# Track active exec sessions: {sid: exec_socket}
exec_sessions = {}


def register_terminal_events(socketio):
    """Register all SocketIO event handlers for the terminal."""

    @socketio.on('connect', namespace='/terminal')
    def handle_connect():
        if not current_user.is_authenticated:
            disconnect()
            return

        logger.info(f"Terminal connected: user={current_user.username} sid={request.sid}")
        emit('output', {'data': '\r\n\x1b[32m[CTFArena]\x1b[0m Conectando a la instancia...\r\n'})

    @socketio.on('start_terminal', namespace='/terminal')
    def handle_start_terminal(data):
        """Initialize the exec session when user opens terminal."""
        if not current_user.is_authenticated:
            disconnect()
            return

        challenge_id = data.get('challenge_id')
        if not challenge_id:
            emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m Challenge ID no proporcionado.\r\n'})
            return

        # Get the user's container
        container = docker_manager.get_container(current_user.id, challenge_id)
        if not container:
            emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m No hay instancia activa. Vuelve al reto e inicia una.\r\n'})
            return

        try:
            # Create an exec instance with a PTY
            exec_instance = container.client.api.exec_create(
                container.id,
                '/bin/bash',
                stdin=True,
                tty=True,
                stdout=True,
                stderr=True,
                environment={
                    'TERM': 'xterm-256color',
                    'COLUMNS': str(data.get('cols', 80)),
                    'LINES': str(data.get('rows', 24)),
                }
            )

            # Start the exec session with a raw socket
            exec_socket = container.client.api.exec_start(
                exec_instance['Id'],
                socket=True,
                tty=True
            )

            # Store the socket
            sid = request.sid
            exec_sessions[sid] = {
                'socket': exec_socket,
                'exec_id': exec_instance['Id'],
                'container_id': container.id,
                'user_id': current_user.id,
                'challenge_id': challenge_id,
            }

            emit('output', {'data': '\r\n\x1b[32m[CTFArena]\x1b[0m ¡Conectado! Buena suerte 🚩\r\n\r\n'})

            # Start reading output from container in a background thread
            thread = threading.Thread(
                target=_read_output,
                args=(socketio, sid, exec_socket),
                daemon=True
            )
            thread.start()

        except Exception as e:
            logger.error(f"Failed to start exec: {e}")
            emit('output', {'data': f'\r\n\x1b[31m[Error]\x1b[0m No se pudo conectar: {str(e)}\r\n'})

    @socketio.on('input', namespace='/terminal')
    def handle_input(data):
        """Forward user input to the container."""
        sid = request.sid
        session = exec_sessions.get(sid)

        if not session:
            return

        try:
            raw_data = data.get('data', '')
            socket = session['socket']
            # Write to the exec socket
            socket._sock.sendall(raw_data.encode('utf-8'))
        except Exception as e:
            logger.error(f"Input error: {e}")
            emit('output', {'data': '\r\n\x1b[31m[Error]\x1b[0m Conexión perdida.\r\n'})
            _cleanup_session(sid)

    @socketio.on('resize', namespace='/terminal')
    def handle_resize(data):
        """Handle terminal resize events."""
        sid = request.sid
        session = exec_sessions.get(sid)

        if not session:
            return

        try:
            cols = data.get('cols', 80)
            rows = data.get('rows', 24)
            container = docker_manager.client.containers.get(session['container_id'])
            container.client.api.exec_resize(
                session['exec_id'],
                height=rows,
                width=cols
            )
        except Exception as e:
            logger.debug(f"Resize error (non-critical): {e}")

    @socketio.on('disconnect', namespace='/terminal')
    def handle_disconnect():
        """Clean up exec session on disconnect."""
        sid = request.sid
        _cleanup_session(sid)
        logger.info(f"Terminal disconnected: sid={sid}")


def _read_output(socketio, sid, exec_socket):
    """Background thread: read output from container and send to browser."""
    try:
        while sid in exec_sessions:
            try:
                # Read from the Docker exec socket
                data = exec_socket._sock.recv(4096)
                if not data:
                    break

                # Send to the browser via SocketIO
                socketio.emit('output', {
                    'data': data.decode('utf-8', errors='replace')
                }, namespace='/terminal', to=sid)

            except ConnectionResetError:
                break
            except OSError:
                break
            except Exception as e:
                logger.error(f"Read error: {e}")
                break

    finally:
        # Notify user that connection ended
        socketio.emit('output', {
            'data': '\r\n\x1b[33m[CTFArena]\x1b[0m Sesión finalizada.\r\n'
        }, namespace='/terminal', to=sid)
        _cleanup_session(sid)


def _cleanup_session(sid):
    """Clean up an exec session."""
    session = exec_sessions.pop(sid, None)
    if session:
        try:
            session['socket']._sock.close()
        except Exception:
            pass
