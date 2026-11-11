import hashlib

ACCESS_RECORD_SESSION_KEY = "_inventario_access_record_id"


def hash_session_key(session_key: str) -> str:
    return hashlib.sha256(session_key.encode("utf-8")).hexdigest()
