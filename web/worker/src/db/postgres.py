from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# Создание асинхронного движка SQLAlchemy с параметрами из настроек
engine = create_async_engine(settings.db.dsn, echo=settings.db.show_query, future=True)
# Создание фабрики сессий
session_factory = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass