from collections.abc import AsyncGenerator
import uuid


from fastapi import Depends
from sqlalchemy import Column, Text, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase


DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Use SQLite for testing 

class Base(DeclarativeBase):
    pass



class User(SQLAlchemyBaseUserTableUUID, Base):
    posts = relationship("Post", back_populates="user")



class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(String, nullable=False)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts")

#start database engine and session maker
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

#create database and tables
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

#create a session that will allow us to interact with the database asynchronously
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

#get user database for fastapi-users
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)