import os
import json
import csv
from fastapi import APIRouter, HTTPException, Query
from typing import List
from backend.schemas.movie import movie
from backend.schemas.movieReviews import movieReviews, movieReviewsCreate, movieReviewsUpdate
from backend.schemas.leaderboard import ReviewerStats, LeaderboardEntry
from backend.services.leaderboardService import generateLeaderboard, calculateReviewerStats
from backend.users.user import User

router = APIRouter()

# load data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

movieReviews_memory = {}


# Load reviews from CSV files at startup
def loadReviewsFromCSV():
    """Load all reviews from CSV files into movieReviews_memory"""
    for movie_folder in os.listdir(DATA_PATH):
        movie_path = os.path.join(DATA_PATH, movie_folder)
        if os.path.isdir(movie_path):
            csv_path = os.path.join(movie_path, "movieReviews.csv")
            if os.path.exists(csv_path):
                reviews = []
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            try:
                                # Clean and validate data
                                usefulness = row.get("Usefulness Vote", "0").strip()
                                total_votes = row.get("Total Votes", "0").strip()
                                rating = row.get("User's Rating out of 10", "0").strip()
                                review_text = row.get("Review", "")[:5000]  # Truncate to 5000 chars
                                
                                # Skip rows with invalid numeric data
                                if not usefulness.isdigit() or not total_votes.isdigit():
                                    continue
                                    
                                # Convert CSV row to movieReviews object
                                review = movieReviews(
                                    dateOfReview=row.get("Date of Review", ""),
                                    user=row.get("User", ""),
                                    usefulnessVote=int(usefulness),
                                    totalVotes=int(total_votes),
                                    userRatingOutOf10=float(rating) if rating.replace('.', '', 1).isdigit() else 0.0,
                                    reviewTitle=row.get("Review Title", "")[:200],  # Truncate to 200 chars
                                    review=review_text
                                )
                                reviews.append(review)
                            except Exception as e:
                                # Skip individual reviews that fail validation
                                continue
                    if reviews:
                        movieReviews_memory[movie_folder.lower()] = reviews
                        print(f"Loaded {len(reviews)} reviews for {movie_folder}")
                except Exception as e:
                    print(f"Error loading reviews for {movie_folder}: {e}")

# Load reviews at module import time
loadReviewsFromCSV()


# helper to get review
def getReviewsForMovie(title: str) -> List[movieReviews]:
    """Return reviews for a given movie title."""
    return movieReviews_memory.get(title.lower(), [])


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


# leaderboard endpoints

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def getTopReviewers():
    """
    Get the top 10 reviewers leaderboard based on helpfulness score.
    
    Helpfulness score = (total_usefulness_votes * usefulness_ratio) + (total_reviews * 10)
    This rewards both quality (usefulness ratio) and quantity (number of reviews).
    
    Returns the top 10 reviewers who have written at least 1 review.
    """
    leaderboard = generateLeaderboard(movieReviews_memory, limit=10, min_reviews=1)
    return leaderboard


@router.get("/stats/{username}", response_model=ReviewerStats)
def getReviewerStats(username: str):
    """Get detailed statistics for a specific reviewer."""
    all_stats = calculateReviewerStats(movieReviews_memory)
    
    stats = all_stats.get(username.lower())
    if not stats:
        raise HTTPException(status_code=404, detail=f"No reviews found for user '{username}'")
    
    return stats
