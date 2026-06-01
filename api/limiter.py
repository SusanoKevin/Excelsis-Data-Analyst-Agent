import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from api.auth import decode_token


def _user_or_ip(request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        user = decode_token(auth[7:])
        if user:
            return user.user_id
    return get_remote_address(request)


_storage = os.getenv("REDIS_URI") or "memory://"
limiter   = Limiter(key_func=_user_or_ip, storage_uri=_storage)
