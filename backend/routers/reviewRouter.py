import os
import json
from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.movie import movie
from backend.schemas.movieReviews import movieReviews, movieReviewsCreate, movieReviewsUpdate
from backend.users.user import User
from backend.repositories.itemsRepo import loadReviews

router = APIRouter()

# load data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

movieReviews_memory = {}


# helper to get review
def getReviewsForMovie(title: str) -> List[movieReviews]:
    """Return reviews for a given movie title, loading from disk if not in memory."""
    title_key = title.lower()
    
    # Check if reviews are in memory
    if title_key in movieReviews_memory:
        return movieReviews_memory[title_key]
    
    # Load reviews from disk
    review_dicts = loadReviews(title)
    if review_dicts:
        # Map CSV field names to Pydantic model field names
        field_mapping = {
            "Date of Review": "dateOfReview",
            "User": "user",
            "Usefulness Vote": "usefulnessVote",
            "Total Votes": "totalVotes",
            "User's Rating out of 10": "userRatingOutOf10",
            "Review Title": "reviewTitle",
            "Review": "review"
        }
        
        # Convert CSV dictionaries to model-compatible dictionaries
        mapped_reviews = []
        for review in review_dicts:
            try:
                mapped_review = {field_mapping.get(k, k): v for k, v in review.items()}
                # Convert numeric fields from strings
                if 'usefulnessVote' in mapped_review:
                    mapped_review['usefulnessVote'] = int(mapped_review['usefulnessVote'])
                if 'totalVotes' in mapped_review:
                    mapped_review['totalVotes'] = int(mapped_review['totalVotes'])
                if 'userRatingOutOf10' in mapped_review:
                    # Skip malformed rating values
                    rating_str = mapped_review['userRatingOutOf10'].strip()
                    if not rating_str or '\n' in rating_str:
                        continue  # Skip this review
                    mapped_review['userRatingOutOf10'] = float(rating_str)
                mapped_reviews.append(mapped_review)
            except (ValueError, KeyError):
                # Skip malformed reviews
                continue
        
            # Convert to movieReviews objects and cache in memory
            reviews = []
            for review in mapped_reviews:
                try:
                    reviews.append(movieReviews(**review))
                except Exception:
                    # Skip reviews that fail Pydantic validation (e.g., too long)
                    continue
            
            if reviews:
                movieReviews_memory[title_key] = reviews
                return reviews
    
    return []
# list all reviews for a movie

# - Returns 404 if:
#     1. No review exists in movieReviews_memory for that movie.
#     2. Movie folder does not exist (checked via DATA_PATH).
# - To test successfully in Swagger:
#     - Add a review first using POST.
#     - Then GET will return the review(s).

@router.get("/{title}/reviews", response_model=List[movieReviews])
def getAllReviewsForMovie(title: str):
    """Return all reviews for a specific movie."""
    movie_folder = os.path.join(DATA_PATH, title)
    if not os.path.exists(movie_folder):
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    reviews = getReviewsForMovie(title)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this movie")
    return reviews


# list all reviews by a user

# - Returns 404 if the user has no reviews.
# - Works case-insensitively.
# - Returns reviews across multiple movies.
# - Unit tests cover all cases: success, case-insensitive, multiple movies, not found.

@router.get("/user/{username}", response_model=List[movieReviews])
def getReviewsByUser(username: str):
    """Return all reviews written by a specific user across all movies."""
    userReviews = []
    for reviews in movieReviews_memory.values():
        for r in reviews:
            if r.user.lower() == username.lower():
                userReviews.append(r)

    if not userReviews:
        raise HTTPException(status_code=404, detail="No reviews found for this user")
    return userReviews


# update review

# - Requires:
#     1. Movie folder exists.
#     2. Index is valid (within list bounds).
#     3. Logged-in user matches the review owner, or user is an admin.
# - Unit tests cover:
#     - Success
#     - Unauthenticated (401)
#     - Index not found (404)
#     - Wrong user (403)
#     - Movie missing (404)

@router.put("/{title}/review/{index}", response_model=movieReviews)
def updateReview(title: str, index: int, updated_data: movieReviewsUpdate, sessionToken: str):
    """Update an existing review by index for a specific movie."""
    current_user = User.getCurrentUser(User, sessionToken)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to Update Reviews")

    movie_folder = os.path.join(DATA_PATH, title)
    if not os.path.exists(movie_folder):
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    reviews = movieReviews_memory.get(title.lower(), [])
    if not reviews or index >= len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")

    if reviews[index].user.lower() != current_user.username.lower():
        raise HTTPException(status_code=403, detail="You can't update others' reviews")
    
    updatedReview = movieReviews(
    user=reviews[index].user,
    **updated_data.dict(exclude={"user"})
    )
    reviews[index] = updatedReview

    movieReviews_memory[title.lower()] = reviews
    return updatedReview


# delete review

# - Same rules as Update:
#     - Movie must exist
#     - Index valid
#     - User must be review owner or admin
# - Unit tests cover:
#     - Success
#     - Unauthenticated (401)
#     - Movie missing (404)
#     - Index out of range (404)
#     - Wrong user (403)
#     - Admin override

@router.delete("/{title}/review/{index}")
def deleteReview(title: str, index: int, sessionToken: str):
    """Delete a review by index for a specific movie."""
    current_user = User.getCurrentUser(User, sessionToken)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to Delete Reviews")

    movie_folder = os.path.join(DATA_PATH, title)
    if not os.path.exists(movie_folder):
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")
    
    # Get the list of reviews
    reviews = movieReviews_memory.get(title.lower(), [])
    if not reviews or index >= len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")
    
    review_to_remove = reviews[index]
    # Allow deletion if current_user is the creator or is an admin
    if (current_user.username.lower() != review_to_remove.user.lower() 
            and getattr(current_user, "role", None) != "admin"):
        raise HTTPException(status_code=403, detail="You can't delete others' reviews")
   
    removed = reviews.pop(index)
    movieReviews_memory[title.lower()] = reviews
    return {"message": f"Deleted review '{removed.reviewTitle}' by {removed.user}"}