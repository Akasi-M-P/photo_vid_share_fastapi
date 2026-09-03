from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from .schemas import PostCreate
from .db import Post, get_async_session, create_db_and_tables
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from .images import imagekit
import imagekitio
import shutil
import os
import uuid
import tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_post(
    caption: str = Form(""),
    file: UploadFile = File(...),
    published: bool = Form(True),
    session: AsyncSession = Depends(get_async_session),
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        with open(temp_file_path, "rb") as f:
            file_bytes = f.read()

        # Upload to ImageKit — options are now direct kwargs, and errors raise exceptions
        upload_result = imagekit.files.upload(
            file=file_bytes,
            file_name=file.filename,
            use_unique_file_name=True,
            tags=["backend-uploads"],
        )

        post = Post(
            caption=caption,
            url=upload_result.url,
            file_type="video" if file.content_type.startswith("video/") else "image",
            file_name=upload_result.name,
            published=published,
        )

        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

    except imagekitio.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=f"ImageKit upload failed: {e.response}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()

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


@app.delete("/delete/{post_id}")
#depends on the get_async_session to provide a database session for the delete operation
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session)):
    try:
        #convert the post_id string to a UUID object for querying the database
        post_uuid = uuid.UUID(post_id)

        #query the database for the post with the given UUID
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        #if the post does not exist, raise a 404 HTTP exception
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        #delete the post from the database and commit the transaction
        await session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting post: {str(e)}")

