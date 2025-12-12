from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import uuid
from collections import defaultdict
import logging

from ..database import get_db
from ..models.sql import User as DBUser, Session as DBSession
from ..config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Configuration for JWT
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Rate Limiting Configuration
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 5

request_counts = defaultdict(lambda: defaultdict(int))
request_timestamps = defaultdict(lambda: defaultdict(datetime))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

class UserInDB(BaseModel):
    email: str
    hashed_password: str

class User(BaseModel):
    email: str
    role: str

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(db: Session, email: str):
    return db.query(DBUser).filter(DBUser.email == email).first()

async def apply_rate_limit(client_ip: str, endpoint: str):
    now = datetime.now(timezone.utc)
    
    # Clean up old requests
    for ip in request_timestamps:
        for ep in request_timestamps[ip]:
            if (now - request_timestamps[ip][ep]).total_seconds() > RATE_LIMIT_WINDOW_SECONDS:
                request_counts[ip][ep] = 0
                request_timestamps[ip][ep] = now

    request_counts[client_ip][endpoint] += 1
    request_timestamps[client_ip][endpoint] = now

    if request_counts[client_ip][endpoint] > MAX_REQUESTS_PER_WINDOW:
        logger.warning(f"Rate limit exceeded for IP: {client_ip} on endpoint: {endpoint}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

@router.post("/register", response_model=User)
async def register_user(request: Request, user_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    await apply_rate_limit(request.client.host, "register")

    db_user = db.query(DBUser).filter(DBUser.email == user_data.username).first()
    if db_user:
        logger.warning(f"Registration attempt with existing email: {user_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    verification_token = str(uuid.uuid4())
    new_user = DBUser(email=user_data.username, hashed_password=hashed_password, is_verified=False, verification_token=verification_token)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # In a real application, send an email with the verification link
    print(f"Email verification link for {new_user.email}: /verify-email?token={verification_token}")

    return User(email=new_user.email, role=new_user.role)

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.verification_token == token).first()

    if not user:
        logger.warning(f"Invalid verification token provided: {token}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    user.is_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Email successfully verified"}

@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    await apply_rate_limit(request.client.host, "token")

    user = await get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = str(uuid.uuid4())
    refresh_token_db_entry = DBSession(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires,
    )
    db.add(refresh_token_db_entry)
    db.commit()
    db.refresh(refresh_token_db_entry)

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/token/refresh", response_model=Token)
async def refresh_access_token(refresh_token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh an access token using a refresh token.
    """
    refresh_token = refresh_token_request.refresh_token
    db_session = db.query(DBSession).filter(DBSession.refresh_token == refresh_token).first()

    if not db_session or db_session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(DBUser).filter(DBUser.id == db_session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Update the session with the new access token
    db_session.session_token = new_access_token
    db.add(db_session)
    db.commit()

    return {"access_token": new_access_token, "token_type": "bearer", "refresh_token": refresh_token}

async def get_current_session(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)) -> DBSession:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        user = db.query(DBUser).filter(DBUser.email == email).first()
        if user is None:
            raise credentials_exception

        active_session = db.query(DBSession).filter(
            DBSession.user_id == user.id,
            DBSession.session_token == token,
            DBSession.expires_at > datetime.now(timezone.utc)
        ).first()

        if not active_session:
            raise credentials_exception
        
        return active_session

    except JWTError:
        raise credentials_exception

@router.post("/logout")
async def logout(current_session: Annotated[DBSession, Depends(get_current_session)], db: Session = Depends(get_db)):
    """
    Logout the current user by invalidating the session.
    """
    db.delete(current_session)
    db.commit()
    logger.info(f"User session for user_id {current_session.user_id} successfully logged out.")
    return {"message": "Successfully logged out"}

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.email == request.email).first()
    if not user:
        logger.warning(f"Forgot password attempt for non-existent user: {request.email}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1) # Token valid for 1 hour
    db.add(user)
    db.commit()
    db.refresh(user)

    # In a real application, send an email with the reset link
    print(f"Password reset link for {user.email}: /reset-password?token={reset_token}")

    return {"message": "Password reset link sent to your email"}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.reset_token == request.token).first()

    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.now(timezone.utc):
        logger.warning(f"Invalid or expired reset token provided: {request.token}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Password has been reset successfully"}

class RefreshTokenRequest(BaseModel):
    refresh_token: str

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("JWT payload missing 'sub' (email).")
            raise credentials_exception
        user = db.query(DBUser).filter(DBUser.email == email).first()
        if user is None:
            logger.warning(f"User not found for email in JWT: {email}")
            raise credentials_exception

        # Check if the access token is still valid in the DBSession table
        active_session = db.query(DBSession).filter(
            DBSession.user_id == user.id,
            DBSession.session_token == token,
            DBSession.expires_at > datetime.now(timezone.utc)
        ).first()

        if not active_session:
            logger.warning(f"Inactive or expired session for user: {email}")
            raise credentials_exception

        if not user.is_verified:
            logger.warning(f"Unverified email access attempt for user: {email}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

        return User(email=user.email, role=user.role)
    except JWTError:
        logger.warning("Invalid JWT token.")
        raise credentials_exception

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]):
        if current_user.role not in self.allowed_roles:
            logger.warning(f"User {current_user.email} with role {current_user.role} attempted to access a protected resource requiring roles: {self.allowed_roles}")
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user

@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(RoleChecker(["user", "admin"]))]):
    return current_user

@router.post("/users/", response_model=User)
async def create_user(user_data: UserCreate, current_user: Annotated[User, Depends(RoleChecker(["admin"]))], db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.email == user_data.email).first()
    if db_user:
        logger.warning(f"Admin user {current_user.email} attempted to create user with existing email: {user_data.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    new_user = DBUser(email=user_data.username, hashed_password=hashed_password, role=user_data.role, is_verified=True) # Admin created users are verified by default
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Admin user {current_user.email} created new user: {new_user.email} with role: {new_user.role}")
    return User(email=new_user.email, role=new_user.role)
