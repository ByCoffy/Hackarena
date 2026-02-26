import docker, threading, time, logging
from datetime import datetime, timezone, timedelta
logger = logging.getLogger(__name__)
client = docker.from_env()
active_containers = {}
container_lock = threading.Lock()
MAX_CONTAINER_LIFETIME = 1800
MAX_CONTAINERS_PER_USER = 1
CLEANUP_INTERVAL = 60

def get_session_key(uid, cid): return f"user_{uid}_chall_{cid}"

def create_container(user_id, challenge_id, image_name, timeout=1800, network_enabled=False, extra_caps=None):
    sk = get_session_key(user_id, challenge_id)
    with container_lock:
        if sk in active_containers:
            ex = active_containers[sk]
            try:
                c = client.containers.get(ex['container_id'])
                if c.status == 'running': return ex
                else: _remove_container(ex['container_id']); del active_containers[sk]
            except docker.errors.NotFound: del active_containers[sk]
        ucs = [k for k in active_containers if k.startswith(f"user_{user_id}_")]
        if len(ucs) >= MAX_CONTAINERS_PER_USER:
            _stop_by_key(ucs[0])
    try:
        cfg = {'image': image_name, 'detach': True, 'stdin_open': True, 'tty': True,
               'mem_limit': '256m', 'cpu_period': 100000, 'cpu_quota': 50000, 'pids_limit': 100,
               'security_opt': ['no-new-privileges'], 'cap_drop': ['ALL'], 'cap_add': ['SETUID','SETGID'],
               'labels': {'ctf.user_id': str(user_id), 'ctf.challenge_id': str(challenge_id), 'ctf.session_key': sk},
               'name': f"ctf_{sk}_{int(time.time())}"}
        if not network_enabled: cfg['network_mode'] = 'none'
        if extra_caps: cfg['cap_add'] = list(set(cfg['cap_add'] + extra_caps))
        container = client.containers.run(**cfg)
        info = {'container_id': container.id, 'session_key': sk, 'user_id': user_id, 'challenge_id': challenge_id,
                'image': image_name, 'created_at': datetime.now(timezone.utc),
                'expires_at': datetime.now(timezone.utc) + timedelta(seconds=timeout), 'timeout': timeout}
        with container_lock: active_containers[sk] = info
        return info
    except docker.errors.ImageNotFound: logger.error(f"Image not found: {image_name}"); return None
    except docker.errors.APIError as e: logger.error(f"Docker API error: {e}"); return None

def stop_container(uid, cid): return _stop_by_key(get_session_key(uid, cid))
def _stop_by_key(sk):
    with container_lock:
        if sk not in active_containers: return False
        info = active_containers[sk]; _remove_container(info['container_id']); del active_containers[sk]
    return True

def get_container(uid, cid):
    sk = get_session_key(uid, cid)
    with container_lock:
        if sk not in active_containers: return None
        info = active_containers[sk]
    try:
        c = client.containers.get(info['container_id'])
        if c.status != 'running':
            with container_lock: active_containers.pop(sk, None)
            return None
        return c
    except docker.errors.NotFound:
        with container_lock: active_containers.pop(sk, None)
        return None

def get_container_info(uid, cid):
    with container_lock: return active_containers.get(get_session_key(uid, cid))

def get_time_remaining(uid, cid):
    info = get_container_info(uid, cid)
    if not info: return 0
    return max(0, int((info['expires_at'] - datetime.now(timezone.utc)).total_seconds()))

def _remove_container(cid):
    try: client.containers.get(cid).kill()
    except: pass
    try: client.containers.get(cid).remove(force=True)
    except: pass

def cleanup_expired():
    now = datetime.now(timezone.utc); expired = []
    with container_lock:
        for k, i in active_containers.items():
            if now > i['expires_at']: expired.append((k, i['container_id']))
    for k, c in expired:
        _remove_container(c)
        with container_lock: active_containers.pop(k, None)

def start_cleanup_thread():
    def _loop():
        while True:
            try: cleanup_expired()
            except: pass
            time.sleep(CLEANUP_INTERVAL)
    threading.Thread(target=_loop, daemon=True).start()

def get_active_container_count():
    with container_lock: return len(active_containers)
def get_all_active_containers():
    with container_lock: return list(active_containers.values())
def is_image_available(name):
    try: client.images.get(name); return True
    except docker.errors.ImageNotFound: return False
