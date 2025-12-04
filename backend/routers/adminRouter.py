import os
import json
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List, Dict, Any
from pathlib import Path
from backend.schemas.movie import movieCreate
from backend.users.user import User
from backend.users.penaltyPoints import PenaltyPoints
from backend.services.moviesService import listMovies
from backend.routers.reviewRouter import movieReviews_memory

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

# Get all users
@router.get("/users")
def getAllUsers(sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Get all users with their details (admin only)."""
    verifyAdminSession(sessionToken)
    
    users = []
    for username, user in User.usersDb.items():
        users.append({
            "username": user.username,
            "email": user.email,
            "isAdmin": user.isAdmin,
            "totalPenaltyPoints": user.totalPenaltyPoints(),
            "totalPenalties": len(user.penaltyPointsList),
            "isVerified": user.isVerified
        })
    
    return {
        "totalUsers": len(users),
        "users": users
    }

# Get user details by username
@router.get("/users/{username}")
def getUserDetails(username: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Get detailed information about a specific user (admin only)."""
    verifyAdminSession(sessionToken)
    
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User.usersDb[username]
    
    # Get user's reviews
    userReviews = []
    if username in movieReviews_memory:
        for movie, review in movieReviews_memory[username].items():
            userReviews.append({
                "movie": movie,
                "rating": review.get("rating"),
                "reviewTitle": review.get("reviewTitle"),
                "review": review.get("review"),
                "dateOfReview": review.get("dateOfReview")
            })
    
    # Get penalty details
    penalties = []
    for penalty in user.penaltyPointsList:
        penalties.append({
            "points": penalty.points,
            "reason": penalty.reason,
            "dateAssigned": penalty.dateAssigned.isoformat() if hasattr(penalty, 'dateAssigned') else None,
            "isExpired": penalty.isExpired() if hasattr(penalty, 'isExpired') else False
        })
    
    return {
        "username": user.username,
        "email": user.email,
        "isAdmin": user.isAdmin,
        "isVerified": user.isVerified,
        "totalPenaltyPoints": user.totalPenaltyPoints(),
        "penalties": penalties,
        "reviews": userReviews,
        "reviewCount": len(userReviews)
    }

# Get all penalty points for a user
@router.get("/users/{username}/penalties")
def getUserPenalties(username: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Get all penalty points for a specific user (admin only)."""
    verifyAdminSession(sessionToken)
    
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User.usersDb[username]
    
    penalties = []
    for i, penalty in enumerate(user.penaltyPointsList):
        penalties.append({
            "index": i,
            "points": penalty.points,
            "reason": penalty.reason,
            "dateAssigned": penalty.dateAssigned.isoformat() if hasattr(penalty, 'dateAssigned') else None,
            "isExpired": penalty.isExpired() if hasattr(penalty, 'isExpired') else False
        })
    
    return {
        "username": username,
        "totalPenaltyPoints": user.totalPenaltyPoints(),
        "penalties": penalties
    }

# Remove penalty from user
@router.delete("/users/{username}/penalties/{penaltyIndex}")
def removePenalty(username: str, penaltyIndex: int, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Remove a specific penalty from a user (admin only)."""
    verifyAdminSession(sessionToken)
    
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User.usersDb[username]
    
    if penaltyIndex < 0 or penaltyIndex >= len(user.penaltyPointsList):
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    removedPenalty = user.penaltyPointsList.pop(penaltyIndex)
    
    return {
        "message": f"Removed penalty from {username}",
        "removedPenalty": {
            "points": removedPenalty.points,
            "reason": removedPenalty.reason
        },
        "remainingPenaltyPoints": user.totalPenaltyPoints()
    }

# Get system statistics
@router.get("/stats")
def getSystemStats(sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Get overall system statistics (admin only)."""
    verifyAdminSession(sessionToken)
    
    # User stats
    totalUsers = len(User.usersDb)
    adminUsers = sum(1 for user in User.usersDb.values() if user.isAdmin)
    verifiedUsers = sum(1 for user in User.usersDb.values() if user.isVerified)
    usersWithPenalties = sum(1 for user in User.usersDb.values() if user.totalPenaltyPoints() > 0)
    
    # Movie stats
    allMovies = listMovies()
    totalMovies = len(allMovies)
    
    # Review stats
    totalReviews = 0
    totalRatings = 0
    for userReviews in movieReviews_memory.values():
        if isinstance(userReviews, list):
            totalReviews += len(userReviews)
            for review in userReviews:
                if isinstance(review, dict) and review.get("rating"):
                    totalRatings += review.get("rating")
        elif isinstance(userReviews, dict):
            totalReviews += len(userReviews)
            for review in userReviews.values():
                if isinstance(review, dict) and review.get("rating"):
                    totalRatings += review.get("rating")
    
    avgRating = totalRatings / totalReviews if totalReviews > 0 else 0
    
    return {
        "users": {
            "total": totalUsers,
            "admins": adminUsers,
            "verified": verifiedUsers,
            "withPenalties": usersWithPenalties
        },
        "movies": {
            "total": totalMovies
        },
        "reviews": {
            "total": totalReviews,
            "averageRating": round(avgRating, 2)
        }
    }

# Update movie metadata
@router.put("/movies/{title}")
def updateMovie(title: str, movieData: movieCreate, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Update movie metadata (admin only)."""
    verifyAdminSession(sessionToken)
    
    folderPath = os.path.join(DATA_PATH, title)
    if not os.path.exists(folderPath):
        raise HTTPException(status_code=404, detail="Movie not found")
    
    try:
        metadataPath = os.path.join(folderPath, "metadata.json")
        
        with open(metadataPath, "w", encoding="utf-8") as f:
            json.dump(movieData.model_dump(), f, indent=4)
        
        # If title changed, rename folder
        if movieData.title != title:
            newFolderPath = os.path.join(DATA_PATH, movieData.title)
            if os.path.exists(newFolderPath):
                raise HTTPException(status_code=400, detail="A movie with the new title already exists")
            os.rename(folderPath, newFolderPath)
            return {"message": f"Movie updated and renamed from '{title}' to '{movieData.title}'"}
        
        return {"message": f"Movie '{title}' updated successfully"}
    except PermissionError:
        raise HTTPException(status_code=500, detail="Permission denied: Unable to update movie")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"IO error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Get all movies (for admin management)
@router.get("/movies")
def getAllMoviesAdmin(sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Get all movies with full details for admin management."""
    verifyAdminSession(sessionToken)
    
    movies = listMovies()
    movieList = []
    
    for movie in movies:
        movieDict = movie.model_dump()
        
        # Count reviews for this movie
        reviewCount = 0
        for userReviews in movieReviews_memory.values():
            if movie.title in userReviews:
                reviewCount += 1
        
        movieDict["reviewCount"] = reviewCount
        movieList.append(movieDict)
    
    return {
        "totalMovies": len(movieList),
        "movies": movieList
    }

# Delete user account
@router.delete("/users/{username}")
def deleteUser(username: str, sessionToken: Optional[str] = Header(None, alias="session-token")):
    """Delete a user account (admin only)."""
    callerUser = verifyAdminSession(sessionToken)
    
    # Prevent self-deletion
    if callerUser.username == username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove from memory
    del User.usersDb[username]
    
    # Remove from database file
    path = Path("backend/data/Users/userList.json")
    data = {}
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
    
    if username in data:
        del data[username]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    # Remove user's reviews from memory
    if username in movieReviews_memory:
        del movieReviews_memory[username]
    
    return {"message": f"User '{username}' deleted successfully"}
