from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    for key, value in to_encode.items():
        if key in ["sub", "iss", "aud", "jti"] and isinstance(value, int):
            to_encode[key] = str(value)
    
    print(f"DEBUG CREATE: Final to_encode sub type: {type(to_encode.get('sub'))}, value: {to_encode.get('sub')}")

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],options={"verify_sub": False})
        sub_value = payload.get("sub")
        # print(f"DEBUG DECODE: sub type: {type(sub_value)}, value: {sub_value}, full payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        print("JWT Error: Token has expired")
        return None
    except Exception as e:
        print(f"Unexpected JWT Error: {e}, type: {type(e)}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    # print(f"DEBUG: Received token: {credentials.credentials[:50]}...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    # print(f"DEBUG: Payload after decode: {payload}")
    
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("sub")
    # print(f"DEBUG: Extracted user_id: {user_id}")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    # print(f"DEBUG: Queried user: {user}, is_active: {user.is_active if user else 'None'}")
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user