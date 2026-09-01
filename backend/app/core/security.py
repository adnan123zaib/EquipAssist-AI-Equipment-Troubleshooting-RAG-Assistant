from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt has a 72-byte input limit. bcrypt_sha256 avoids silent truncation while
# retaining bcrypt verification compatibility for existing accounts.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expires},
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("Token subject is missing")
        return user_id
    except (JWTError, ValueError) as exc:
        raise ValueError("Invalid or expired access token") from exc


def _fernet() -> Fernet:
    configured = get_settings().app_encryption_key.strip()
    if not configured:
        raise RuntimeError("APP_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(configured.encode())
    except ValueError as exc:
        raise RuntimeError("APP_ENCRYPTION_KEY is invalid") from exc


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
