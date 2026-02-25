"""
Docker Manager - Gestión del ciclo de vida de contenedores para retos interactivos.

Cada usuario obtiene su propio contenedor aislado con recursos limitados.
Los contenedores se auto-destruyen tras un timeout configurable.
"""

import docker
import threading
import time
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Global Docker client
client = docker.from_env()

# Track active containers: {session_key: container_info}
active_containers = {}
container_lock = threading.Lock()


# --- Configuration ---
CONTAINER_DEFAULTS = {
    'mem_limit': '256m',
    'cpu_period': 100000,
    'cpu_quota': 50000,       # 50% of one CPU
    'network_mode': 'none',   # No network by default (security)
    'pids_limit': 100,        # Prevent fork bombs
    'read_only': False,       # Some challenges need write access
    'security_opt': ['no-new-privileges'],
    'cap_drop': ['ALL'],
    'cap_add': ['SETUID', 'SETGID'],  # Needed for privesc challenges
}

MAX_CONTAINER_LIFETIME = 1800   # 30 minutes max
MAX_CONTAINERS_PER_USER = 1     # One active container per user
CLEANUP_INTERVAL = 60           # Check for expired containers every 60s


def get_session_key(user_id, challenge_id):
    """Generate a unique key for user+challenge combination."""
    return f"user_{user_id}_chall_{challenge_id}"


def create_container(user_id, challenge_id, image_name, timeout=MAX_CONTAINER_LIFETIME,
                     network_enabled=False, extra_caps=None):
    """
    Create an isolated Docker container for a user's interactive challenge.

    Returns: dict with container_id, session_key, or None on error
    """
    session_key = get_session_key(user_id, challenge_id)

    with container_lock:
        # Check if user already has a container for this challenge
        if session_key in active_containers:
            existing = active_containers[session_key]
            try:
                container = client.containers.get(existing['container_id'])
                if container.status == 'running':
                    logger.info(f"Reusing existing container for {session_key}")
                    return existing
                else:
                    # Container died, clean it up
                    _remove_container(existing['container_id'])
                    del active_containers[session_key]
            except docker.errors.NotFound:
                del active_containers[session_key]

        # Check max containers per user
        user_containers = [k for k in active_containers if k.startswith(f"user_{user_id}_")]
        if len(user_containers) >= MAX_CONTAINERS_PER_USER:
            # Remove the oldest container
            oldest_key = user_containers[0]
            stop_container(user_id, int(oldest_key.split('_chall_')[1]))

    try:
        # Build container config
        container_config = {
            'image': image_name,
            'detach': True,
            'stdin_open': True,
            'tty': True,
            'mem_limit': CONTAINER_DEFAULTS['mem_limit'],
            'cpu_period': CONTAINER_DEFAULTS['cpu_period'],
            'cpu_quota': CONTAINER_DEFAULTS['cpu_quota'],
            'pids_limit': CONTAINER_DEFAULTS['pids_limit'],
            'security_opt': CONTAINER_DEFAULTS['security_opt'],
            'cap_drop': CONTAINER_DEFAULTS['cap_drop'],
            'cap_add': CONTAINER_DEFAULTS.get('cap_add', []),
            'labels': {
                'ctf.user_id': str(user_id),
                'ctf.challenge_id': str(challenge_id),
                'ctf.session_key': session_key,
                'ctf.created_at': datetime.now(timezone.utc).isoformat(),
            },
            'name': f"ctf_{session_key}_{int(time.time())}",
        }

        # Network isolation
        if not network_enabled:
            container_config['network_mode'] = 'none'

        # Extra capabilities for specific challenges
        if extra_caps:
            container_config['cap_add'] = list(set(
                container_config.get('cap_add', []) + extra_caps
            ))

        container = client.containers.run(**container_config)

        container_info = {
            'container_id': container.id,
            'session_key': session_key,
            'user_id': user_id,
            'challenge_id': challenge_id,
            'image': image_name,
            'created_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=timeout),
            'timeout': timeout,
        }

        with container_lock:
            active_containers[session_key] = container_info

        logger.info(f"Container created: {container.short_id} for {session_key}")
        return container_info

    except docker.errors.ImageNotFound:
        logger.error(f"Image not found: {image_name}")
        return None
    except docker.errors.APIError as e:
        logger.error(f"Docker API error: {e}")
        return None


def stop_container(user_id, challenge_id):
    """Stop and remove a user's container."""
    session_key = get_session_key(user_id, challenge_id)

    with container_lock:
        if session_key not in active_containers:
            return False

        container_info = active_containers[session_key]
        _remove_container(container_info['container_id'])
        del active_containers[session_key]

    logger.info(f"Container stopped: {session_key}")
    return True


def get_container(user_id, challenge_id):
    """Get the Docker container object for a user's session."""
    session_key = get_session_key(user_id, challenge_id)

    with container_lock:
        if session_key not in active_containers:
            return None

        container_info = active_containers[session_key]

    try:
        container = client.containers.get(container_info['container_id'])
        if container.status != 'running':
            # Container died
            with container_lock:
                if session_key in active_containers:
                    del active_containers[session_key]
            return None
        return container
    except docker.errors.NotFound:
        with container_lock:
            if session_key in active_containers:
                del active_containers[session_key]
        return None


def get_container_info(user_id, challenge_id):
    """Get info about a user's active container."""
    session_key = get_session_key(user_id, challenge_id)
    with container_lock:
        return active_containers.get(session_key)


def get_time_remaining(user_id, challenge_id):
    """Get seconds remaining for a container."""
    info = get_container_info(user_id, challenge_id)
    if not info:
        return 0
    remaining = (info['expires_at'] - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(remaining))


def exec_in_container(container, command):
    """Execute a command in a container and return output."""
    try:
        result = container.exec_run(command, tty=True)
        return result.output.decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"Exec error: {e}")
        return None


def _remove_container(container_id):
    """Force remove a container."""
    try:
        container = client.containers.get(container_id)
        container.kill()
    except Exception:
        pass
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
    except Exception:
        pass


def cleanup_expired():
    """Remove all expired containers. Called periodically."""
    now = datetime.now(timezone.utc)
    expired = []

    with container_lock:
        for key, info in active_containers.items():
            if now > info['expires_at']:
                expired.append((key, info['container_id']))

    for key, container_id in expired:
        _remove_container(container_id)
        with container_lock:
            if key in active_containers:
                del active_containers[key]
        logger.info(f"Expired container cleaned up: {key}")


def cleanup_all():
    """Remove ALL CTF containers (for shutdown)."""
    with container_lock:
        for key, info in active_containers.items():
            _remove_container(info['container_id'])
        active_containers.clear()
    logger.info("All CTF containers cleaned up.")


def start_cleanup_thread():
    """Start background thread for periodic container cleanup."""
    def _cleanup_loop():
        while True:
            try:
                cleanup_expired()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            time.sleep(CLEANUP_INTERVAL)

    thread = threading.Thread(target=_cleanup_loop, daemon=True)
    thread.start()
    logger.info("Container cleanup thread started.")


def get_active_container_count():
    """Return count of active containers."""
    with container_lock:
        return len(active_containers)


def get_all_active_containers():
    """Return list of all active containers (for admin panel)."""
    with container_lock:
        return list(active_containers.values())


def is_image_available(image_name):
    """Check if a Docker image exists locally."""
    try:
        client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        return False


def build_challenge_image(dockerfile_path, image_name):
    """Build a Docker image from a Dockerfile."""
    try:
        image, logs = client.images.build(
            path=dockerfile_path,
            tag=image_name,
            rm=True
        )
        return True
    except Exception as e:
        logger.error(f"Build error: {e}")
        return False
