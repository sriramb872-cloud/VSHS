"""
SCHOLARIS ERP - User Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.crud.user import crud_user
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return crud_user.get(self.db, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return crud_user.get_by_email(self.db, email)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return crud_user.get_multi_by_school(self.db, school_id, skip, limit)

    def create(self, obj_in: UserCreate) -> User:
        return crud_user.create(self.db, obj_in)

    def update(self, db_obj: User, obj_in: UserUpdate) -> User:
        return crud_user.update(self.db, db_obj, obj_in)

    def delete(self, user_id: int) -> Optional[User]:
        return crud_user.delete(self.db, user_id)
