import os, time, uuid, jwt
from typing import Optional
from fastapi import HTTPException, Header
from api.schemas import User, Role
from config import settings

def _sign(email: str, name: str, role: str) -> str:
    payload = {
        "sub": email,
        "name": name,
        "role": role,
        "exp": int(time.time()) + settings.jwt_expiry_minutes * 60,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

def saml_login(email: str, name: str, role: str) -> str:
    return _sign(email, name, role)

def oauth_login(email: str, name: str, role: str = Role.viewer.value) -> str:
    return _sign(email, name, role)

def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing Bearer token")
    payload = _decode(authorization.split(None, 1)[1].strip())
    return User(
        id=payload.get("sub", ""),
        email=payload.get("sub", ""),
        name=payload.get("name", ""),
        role=Role(payload.get("role", "viewer")),
    )

def require_role(*roles: Role):
    def dependency(user: User = None) -> User:
        from fastapi import Depends
        user = get_current_user()
        if user.role not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(r.value for r in roles)}")
        return user
    return dependency
