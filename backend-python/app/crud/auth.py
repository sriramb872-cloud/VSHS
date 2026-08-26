from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import UserModel


class CRUDAuth:

    def get_user_by_mobile(
        self,
        db: Session,
        mobile_number: str,
    ) -> Optional[UserModel]:
        return (
            db.query(UserModel)
            .filter(UserModel.mobile == mobile_number)
            .first()
        )

    def get_user_by_id(
        self,
        db: Session,
        user_id: int,
    ) -> Optional[UserModel]:
        return (
            db.query(UserModel)
            .filter(UserModel.id == user_id)
            .first()
        )

    def get_active_user(
        self,
        db: Session,
        mobile_number: str,
    ) -> Optional[UserModel]:
        return (
            db.query(UserModel)
            .filter(
                UserModel.mobile == mobile_number,
                UserModel.is_active == "ACTIVE",
            )
            .first()
        )


auth_crud = CRUDAuth()