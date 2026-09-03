from fastapi import FastAPI,HTTPException
from .schemas import PostCreate
from .db import Post, get_async_session, create_db_and_tables
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database and tables before the application starts
    await create_db_and_tables()
    yield
    # Perform any cleanup tasks after the application shuts down (if needed)

app = FastAPI(lifespan=lifespan)

textPost = {
    1: {
        "title": "A Beautiful Morning",
        "content": "Every morning is a new opportunity to start again, set new goals, and make progress."
    },
    2: {
        "title": "Keep Learning",
        "content": "The world keeps changing, so never stop learning. Every new skill can open a door to a new opportunity."
    },
    3: {
        "title": "Weekend Adventure",
        "content": "Sometimes the best way to recharge is to step outside, explore somewhere new, and enjoy the little things."
    },
    4: {
        "title": "Technology Today",
        "content": "Technology continues to change how we work, communicate, learn, and solve everyday problems."
    },
    5: {
        "title": "Small Steps",
        "content": "You don't have to accomplish everything at once. Small consistent steps can eventually lead to significant results."
    },
    6: {
        "title": "Good Friends",
        "content": "Having people around who encourage, support, and challenge you can make the journey much more meaningful."
    },
    7: {
        "title": "Stay Positive",
        "content": "Not every day will go according to plan, but staying positive can help you find a way forward."
    },
    8: {
        "title": "The Power of Ideas",
        "content": "A simple idea can become something powerful when you combine creativity, patience, and consistent effort."
    },
    9: {
        "title": "Enjoy the Journey",
        "content": "Success is not only about reaching the destination. Take time to appreciate the experiences and lessons along the way."
    },
    10: {
        "title": "New Beginnings",
        "content": "Starting something new can be challenging, but every beginning brings an opportunity to grow and discover something different."
    }
}

@app.get("/posts")
def get_posts(limit: int ):
    if limit:
       return list(textPost.values())[:limit]
    return textPost

@app.get("/posts/{post_id}")
def get_post(post_id: int):
    if post_id in textPost:
        return textPost[post_id]
    else:
        raise HTTPException(status_code=404, detail="Post not found")

@app.post("/posts")
def create_post(post: PostCreate):
    new_post = {
        "title": post.title,
        "content": post.content,
        "published": post.published
    }
    textPost[max(textPost.keys()) + 1] = new_post
    return new_post

@app.delete("/posts/{post_id}")
def delete_post(post_id: int):
    if post_id in textPost:
        deleted_post = textPost.pop(post_id)
        return {"message": "Post deleted successfully", "post": deleted_post}
    else:
        raise HTTPException(status_code=404, detail="Post not found")
