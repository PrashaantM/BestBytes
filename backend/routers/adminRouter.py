import os
import json
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pathlib import Path
from backend.schemas.movie import movieCreate
from backend.users.user import User
from backend.users.penaltyPoints import PenaltyPoints

router = APIRouter()

# load data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

def verifyAdminSession(sessionToken: Optional[str]) -> User:
    """Verify that the session token belongs to an admin user"""
    if not sessionToken:
        raise HTTPException(status_code=401, detail="Session token required")
    
    # Use getCurrentUser to validate session and get user
    user = User.getCurrentUser(sessionToken)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if not user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return user

@router.post("/promote")
def promoteToAdmin(username: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Promote a user to admin status (admin only)"""
    # Verify caller is admin
    verifyAdminSession(sessionToken)
    
    # Check if target user exists
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    targetUser = User.usersDb[username]
    
    if targetUser.isAdmin:
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    # Promote user
    targetUser.isAdmin = True
    
    # Update in database
    path = Path("backend/data/Users/userList.json")
    data = {}
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
    
    if username in data:
        data[username]["isAdmin"] = True
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    return {"message": f"User '{username}' promoted to admin"}

@router.post("/demote")
def demoteFromAdmin(username: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Remove admin status from a user (admin only)"""
    # Verify caller is admin
    callerUser = verifyAdminSession(sessionToken)
    
    # Prevent self-demotion
    if callerUser.username == username:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    
    # Check if target user exists
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    targetUser = User.usersDb[username]
    
    if not targetUser.isAdmin:
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    # Demote user
    targetUser.isAdmin = False
    
    # Update in database
    path = Path("backend/data/Users/userList.json")
    data = {}
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
    
    if username in data:
        data[username]["isAdmin"] = False
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    return {"message": f"User '{username}' demoted from admin"}

# add new movie

# - Adds a new movie folder under DATA_PATH and creates a metadata.json file.
# - Returns 400 if the movie already exists.
# - Returns 500 for permission issues or unexpected IO errors.
# - In Swagger, provide all required movie fields in JSON.

@router.post("/add-movie")
def addMovie(movieData: movieCreate, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Add a new movie folder and metadata file (admin only)."""
    # Verify caller is admin
    verifyAdminSession(sessionToken)
    
    folderPath = os.path.join(DATA_PATH, movieData.title)
    if os.path.exists(folderPath):
        raise HTTPException(status_code=400, detail="Movie already exists")

    try:
        os.makedirs(folderPath, exist_ok=True)
        metadataPath = os.path.join(folderPath, "metadata.json")

        with open(metadataPath, "w", encoding="utf-8") as f:
            json.dump(movieData.model_dump(), f, indent=4)

        return {"message": f"Movie '{movieData.title}' added successfully."}
    except PermissionError:
        raise HTTPException(status_code=500, detail="Permission denied: Unable to create movie folder")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"IO error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
# delete movie

# - Deletes the movie folder and its metadata.json file.
# - Returns 404 if the folder does not exist.
# - Returns 500 for permission issues or OS errors during deletion.
# - Be careful: deletes all files inside the folder before removing it.
# - Swagger: Just input the movie title in the path.

@router.delete("/delete-movie/{title}")
def deleteMovie(title: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Delete a movie folder and its metadata file (admin only)."""
    # Verify caller is admin
    verifyAdminSession(sessionToken)
    
    folderPath = os.path.join(DATA_PATH, title)
    if not os.path.exists(folderPath):
        raise HTTPException(status_code=404, detail="Movie not found")

    try:
        for fileName in os.listdir(folderPath):
            os.remove(os.path.join(folderPath, fileName))
        os.rmdir(folderPath)

        return {"message": f"Movie '{title}' deleted successfully."}
    except PermissionError:
        raise HTTPException(status_code=500, detail="Permission denied: Unable to delete movie")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error deleting movie: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# assign penalty to user

# - Assigns penalty points to a user.
# - Returns 404 if the user does not exist.
# - Each user has a 'penalties' list; new penalties are appended.
# - Returns 500 if the internal logic fails (e.g., User.usersDb not set properly).
# - Swagger requires query params:
#     - username (string)
#     - points (integer)
#     - reason (string)
# - Example URL: /admin/penalty?username=khushi&points=2&reason=hate%20speech
# - Make sure the user exists in User.usersDb before testing.

@router.post("/penalty")
def assignPenalty(username: str, points: int, reason: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Assign penalty points to a user (admin only)."""
    # Verify caller is admin
    verifyAdminSession(sessionToken)
    
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")

    user = User.usersDb[username]

    # Create a PenaltyPoints object (automatically adds to user's penaltyPointsList)
    PenaltyPoints(points=points, user=user, reason=reason)
    
    # Calculate total active penalty points
    totalPoints = user.totalPenaltyPoints()
    
    return {
        "message": f"Assigned {points} penalty points to {username}",
        "totalPenaltyPoints": totalPoints,
        "totalPenalties": len(user.penaltyPointsList),
    }