from fastapi import FastAPI,HTTPException, Depends,File, UploadFile, Form
from .schemas import PostCreate
from .db import Post, get_async_session, create_db_and_tables
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database and tables before the application starts
    await create_db_and_tables()
    yield
    # Perform any cleanup tasks after the application shuts down (if needed)

app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_post(
    caption: str = Form(""),  # Default caption if not provided
    file: UploadFile = File(...),  # Accept any file type
    published: bool = Form(True),  # Default published status if not provided
    session: AsyncSession = Depends(get_async_session)
):
    post = Post(
        caption=caption,
        url="dummy url",  # Assuming you will save the file and generate a URL
        file_type="photo",
        file_name="dummy file name",  # Assuming you will save the file and get the actual file name
        published=published
    )

    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post

@app.get("/feed")
async def get_feed(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()

    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
            }
        )

    return {"posts": posts_data}

