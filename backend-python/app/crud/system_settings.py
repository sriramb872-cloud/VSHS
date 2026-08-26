# app/crud/settings.py
from sqlalchemy.orm import Session
from typing import Optional

class CRUDSettings:
    def get_super_admin_settings(self, db: Session):
        return None

    def update_super_admin_settings(self, db: Session, obj_in: dict):
        return obj_in

    def get_principal_settings(self, db: Session, school_id: int):
        return None

    def update_principal_settings(self, db: Session, school_id: int, obj_in: dict):
        return obj_in

    def get_user_settings(self, db: Session, user_id: int):
        return None

    def update_user_settings(self, db: Session, user_id: int, obj_in: dict):
        return obj_in

settings_crud = CRUDSettings()
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
