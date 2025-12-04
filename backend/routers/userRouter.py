import os
from fastapi import APIRouter, HTTPException
from backend.users.user import User
from backend.services.movieRecommendationService import MovieRecommendationService 

router = APIRouter()
recommendSvc = MovieRecommendationService()


# register user
@router.post("/register")
def registerUser(username: str, email: str, password: str):
    """Create a new user account."""
    try:
        newUser = User.createAccount(username=username, email=email, password=password)
        userMovieLists.setdefault(newUser.username.lower(), {})
        userMovieLists[newUser.username.lower()]["watched"] = []
        return {
            "message": "Account created successfully!",
            "username": newUser.username,
            "email": newUser.email,
            "verificationToken": newUser.verificationToken,
            "warning": "⚠️ IMPORTANT: Save your verification token! You must verify your account before logging in. If you lose this token, your account cannot be verified.",
            "instructions": "Use the /users/verify endpoint with your username and this token to verify your account."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# verify email
@router.post("/verify")
def verifyEmail(username: str, token: str):
    """Verify user's email using the verification token."""
    if username not in User.usersDb:
        raise HTTPException(status_code=404, detail="User not found")

    user = User.usersDb[username]
    if user.verifyEmail(token):
        return {"message": "Email verified successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid verification token")

# login user
@router.post("/login")
def loginUser(username: str, password: str):
    """Login a user and return a session token."""
    try:
        sessionToken = User.login(username=username, password=password)
        return {"message": "Login successful!", "sessionToken": sessionToken}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# logout user
@router.post("/logout")
def logoutUser(sessionToken: str):
    """Logout a user by removing their session token."""
    if User.logout(User, sessionToken):
        return {"message": "Logout successful!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired session token")

# get current user
@router.get("/me")
def getCurrentUser(sessionToken: str):
    """Return the current logged-in user's details if session is valid."""
    currentUser = User.getCurrentUser(sessionToken)
    if currentUser:
        return {
            "username": currentUser.username,
            "email": currentUser.email,
            "verified": currentUser.isVerified,
            "createdAt": str(currentUser.createdAt),
            "lastLogin": str(currentUser.lastLogin) if currentUser.lastLogin else None
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

@router.get("/recommendations")
def getUserRecommendations(sessionToken: str):
    """Get movie recommendations for the user."""
    currentUser = User.getCurrentUser(sessionToken)

    if not currentUser:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    
    try:
        recommendations = recommendSvc.recommendMovies(currentUser.username, numRecommendations=5)
    except Exception:
        raise HTTPException(status_code=500, detail="Error generating recommendations")
    
    return recommendations
    
    
