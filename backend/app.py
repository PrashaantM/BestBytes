from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.routers import (
    movieRouter,
    reviewRouter,
    userRouter,
    adminRouter,
    listsRouter
)
from backend.users.user import User
from backend.services.userServices import readAllUsers
from pathlib import Path
import bcrypt

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load users from database on startup"""
    print("Loading users from database...")
    usersData = readAllUsers()
    
    for username, userData in usersData.items():
        try:
            # Create user object from saved data
            user = User.__new__(User)
            user.username = username
            user.email = userData.get("email", "")
            user.passwordHash = userData.get("password", "").encode("utf-8")
            user.isVerified = userData.get("isVerified", False)
            user.verificationToken = userData.get("verificationToken", "")
            user.penaltyPointsList = []
            user.createdAt = None
            user.lastLogin = None
            
            # Add to in-memory database
            User.usersDb[username] = user
            print(f"Loaded user: {username} (verified: {user.isVerified})")
        except Exception as e:
            print(f"Error loading user {username}: {e}")
    
    print(f"Total users loaded: {len(User.usersDb)}")
    yield
    # Cleanup (if needed)
    print("Shutting down...")

app = FastAPI(
    title="BestBytes Movie Review API",
    description="Backend API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movieRouter.router, prefix="/movies", tags=["Movies"])
app.include_router(reviewRouter.router, prefix="/reviews", tags=["Reviews"])
app.include_router(userRouter.router, prefix="/users", tags=["Users"])
app.include_router(adminRouter.router, prefix="/admin", tags=["Admin"])
app.include_router(listsRouter.router, prefix="/lists", tags=["Lists"])

@app.get("/")
def root():
    """endpoint working"""
    return {"message": "API running"}
