from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(401, str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User account is unavailable")
    return user

