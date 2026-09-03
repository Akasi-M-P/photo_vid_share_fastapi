from pydantic import BaseModel
from fastapi_users import schemas
import uuid

class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = True

class PostResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    published: bool

    class Config:
        orm_mode = True

class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass