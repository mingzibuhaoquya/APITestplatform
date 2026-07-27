from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext
from .config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().app_secret, salt="api-test-platform")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps({"user_id": user_id})


def read_session_token(token: str) -> int | None:
    try:
        payload = _serializer().loads(token)
    except BadSignature:
        return None
    return int(payload["user_id"]) if "user_id" in payload else None

