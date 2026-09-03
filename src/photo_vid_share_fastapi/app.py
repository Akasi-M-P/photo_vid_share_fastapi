from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from .schemas import PostCreate, PostResponse, UserRead, UserCreate, UserUpdate
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
from .users import User, current_active_user, auth_backend, fastapi_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the app starts up.
    # create_db_and_tables() creates any tables that don't exist yet —
    # it does NOT alter existing tables if you add/change columns later.
    await create_db_and_tables()
    yield
    # (nothing to clean up on shutdown right now)


app = FastAPI(lifespan=lifespan)

# --- fastapi-users routers: handle login, registration, user management, etc. ---

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)


@app.post("/upload")
async def upload_post(
    caption: str = Form(""),
    file: UploadFile = File(...),
    published: bool = Form(True),
    user: User = Depends(current_active_user),  # requires a logged-in user
    session: AsyncSession = Depends(get_async_session),
):
    temp_file_path = None

    try:
        # Save the uploaded file to a temp file on disk first.
        # (ImageKit's upload() wants bytes/a file, not the raw UploadFile object)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Read the temp file back into memory as bytes for the upload call
        with open(temp_file_path, "rb") as f:
            file_bytes = f.read()

        # Upload to ImageKit.
        # NOTE: in the current SDK, options like tags/use_unique_file_name are
        # passed as direct keyword arguments (not wrapped in an "options" object),
        # and failures raise an exception instead of returning a status code.
        upload_result = imagekit.files.upload(
            file=file_bytes,
            file_name=file.filename,
            use_unique_file_name=True,
            tags=["backend-uploads"],
        )

        # Build the DB row using data returned by ImageKit + the form fields
        post = Post(
            user_id=user.id,  # tie this post to whoever is logged in
            caption=caption,
            url=upload_result.url,
            file_type="video" if file.content_type.startswith("video/") else "image",
            file_name=upload_result.name,
            published=published,
        )

        session.add(post)
        await session.commit()
        await session.refresh(post)  # reload post with DB-generated fields (id, created_at, etc.)
        return post

    except imagekitio.APIStatusError as e:
        # ImageKit-specific error (e.g. bad file, auth issue, rate limit)
        raise HTTPException(status_code=e.status_code, detail=f"ImageKit upload failed: {e.response}")
    except Exception as e:
        # Catch-all for anything else that goes wrong (DB error, disk error, etc.)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        # Always clean up the temp file and close the upload stream,
        # whether the upload succeeded or failed
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),  # needed to compute is_owner per post
):
    # Get all posts, newest first
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()

    # Collect the unique user_ids referenced by these posts, then fetch
    # just those User rows in one query (avoids querying User once per post)
    user_ids = {post.user_id for post in posts}
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()
    user_dict = {u.id: u.email for u in users}  # quick lookup: user_id -> email

    # Manually build a JSON-safe dict per post (UUIDs and datetimes aren't
    # JSON-serializable by default, so convert them here)
    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
                "is_owner": post.user_id == user.id,  # True if the logged-in user posted this
                "email": user_dict.get(post.user_id, "Unknown"),  # poster's email
            }
        )

    return {"posts": posts_data}


@app.delete("/delete/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    try:
        # post_id comes in as a string from the URL; convert to UUID to query the DB
        post_uuid = uuid.UUID(post_id)

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Only the post's owner is allowed to delete it
        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this post")

        await session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting post: {str(e)}")