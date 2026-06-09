"""
Declarative base for all SQLAlchemy 2.0 async models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass