from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User as UserModel
from backend.app.models.role import Role as RoleModel
from backend.app.models.permission import Permission as PermissionModel
from backend.app.auth.jwt import get_current_user
from backend.app.auth.rbac import check_permissions
import uuid

router = APIRouter()

class User(BaseModel):
    id: str
    username: str
    roles: List[str] = []

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str
    roles: List[str] = []

class Role(BaseModel):
    id: str
    name: str
    permissions: List[str] = []

    class Config:
        orm_mode = True

class RoleCreate(BaseModel):
    name: str
    permissions: List[str] = []

class Permission(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True

class PermissionCreate(BaseModel):
    name: str

@router.post("/users", response_model=User, dependencies=[Depends(check_permissions(["user_create"]))])
async def create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new user.
    """
    # In a real app, you would hash the password here
    hashed_password = request.password + "notreallyhashed"
    new_user = UserModel(
        id=str(uuid.uuid4()),
        username=request.username,
        hashed_password=hashed_password,
    )
    for role_name in request.roles:
        role = db.query(RoleModel).filter(RoleModel.name == role_name).first()
        if role:
            new_user.roles.append(role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/users", response_model=List[User], dependencies=[Depends(check_permissions(["user_read"]))])
async def get_users(db: Session = Depends(get_db)):
    """
    Get all users.
    """
    return db.query(UserModel).all()

@router.post("/roles", response_model=Role, dependencies=[Depends(check_permissions(["role_create"]))])
async def create_role(
    request: RoleCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new role.
    """
    new_role = RoleModel(
        id=str(uuid.uuid4()),
        name=request.name,
    )
    for permission_name in request.permissions:
        permission = db.query(PermissionModel).filter(PermissionModel.name == permission_name).first()
        if permission:
            new_role.permissions.append(permission)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@router.get("/roles", response_model=List[Role], dependencies=[Depends(check_permissions(["role_read"]))])
async def get_roles(db: Session = Depends(get_db)):
    """
    Get all roles.
    """
    return db.query(RoleModel).all()

@router.post("/permissions", response_model=Permission, dependencies=[Depends(check_permissions(["permission_create"]))])
async def create_permission(
    request: PermissionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new permission.
    """
    new_permission = PermissionModel(
        id=str(uuid.uuid4()),
        name=request.name,
    )
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    return new_permission

@router.get("/permissions", response_model=List[Permission], dependencies=[Depends(check_permissions(["permission_read"]))])
async def get_permissions(db: Session = Depends(get_db)):
    """
    Get all permissions.
    """
    return db.query(PermissionModel).all()
