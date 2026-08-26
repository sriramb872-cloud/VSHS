"""
SCHOLARIS ERP - User CRUD
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class CRUDUser:
    def get(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_multi_by_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        return db.query(User).filter(User.school_id == school_id).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        hashed_pw = get_password_hash(obj_in.password)
        db_obj = User(
            email=obj_in.email,
            password_hash=hashed_pw,
            display_name=obj_in.full_name,
            role=obj_in.role,
            school_id=obj_in.school_id,
            is_active=obj_in.is_active
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, user_id: int) -> Optional[User]:
        obj = db.query(User).filter(User.id == user_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


crud_user = CRUDUser()
