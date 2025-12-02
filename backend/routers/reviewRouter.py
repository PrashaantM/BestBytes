import os
import json
import csv
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
from backend.schemas.movie import movie
from backend.schemas.movieReviews import movieReviews, movieReviewsCreate, movieReviewsUpdate
from backend.schemas.leaderboard import ReviewerStats, LeaderboardEntry
from backend.services.leaderboardService import generateLeaderboard, calculateReviewerStats
from backend.users.user import User
from backend.repositories.itemsRepo import loadReviews
from backend.services.moviesService import (
    addReview as serviceAddReview,
    getMovieByName,
    updateReview as serviceUpdateReview,
    deleteReview as serviceDeleteReview,
)

router = APIRouter()

# In-memory reviews store used by tests and leaderboard
movieReviews_memory = {}

# Data path for tests that patch filesystem
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")


# add review

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
@router.post("/{title}", response_model=movieReviews)
def addReview(title: str, reviewData: movieReviewsCreate, sessionToken: str = Query(...)):
    """Add a review for a specific movie by title."""

    # user authentication
    currentUser = User.getCurrentUser(User, sessionToken)
    if not currentUser: 
        raise HTTPException(status_code=401, detail="Login required to review")

    # verify movie exists
    try:
        getMovieByName(title)
    except HTTPException:
        # Tests expect a generic "Review not found" when movie is missing
        raise HTTPException(status_code=404, detail="Review not found")

    # validate date format (must be YYYY-MM-DD)
    try:
        datetime.strptime(reviewData.dateOfReview, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Please use YYYY-MM-DD format (e.g., 2025-11-28)"
        )

    # check: review title and text are not empty
    if not reviewData.reviewTitle.strip() or not reviewData.review.strip():
        raise HTTPException(status_code=400, detail="Review title and text cannot be empty")

    # add review using service layer
    return serviceAddReview(title, reviewData)


# list all reviews for a movie

@router.get("/{title}/reviews", response_model=List[movieReviews])
def getAllReviewsForMovie(title: str):
    """Return all reviews for a specific movie."""
    try:
        movie = getMovieByName(title)
        if not movie.reviews:
            raise HTTPException(status_code=404, detail="No reviews found for this movie")
        return movie.reviews
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")


# list all reviews by a user

@router.get("/user/{username}", response_model=List[movieReviews])
def getReviewsByUser(username: str):
    """Return all reviews written by a specific user across all movies."""
    userReviews = []
    from backend.services.moviesService import listMovies
    
    for movie_obj in listMovies():
        for review in movie_obj.reviews:
            if review.user.lower() == username.lower():
                userReviews.append(review)

    if not userReviews:
        raise HTTPException(status_code=404, detail="No reviews found for this user")
    return userReviews


# update review

@router.put("/{title}/review/{index}", response_model=movieReviews)
def updateReview(title: str, index: int, updatedData: movieReviewsUpdate, sessionToken: str = Query(...)):
    """Update an existing review by index for a specific movie."""
    currentUser = User.getCurrentUser(User, sessionToken)
    if not currentUser:
        raise HTTPException(status_code=401, detail="Login required to Update Reviews")

    try:
        movie_obj = getMovieByName(title)
        if not movie_obj.reviews or index >= len(movie_obj.reviews):
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Check if current user is the review owner
        if movie_obj.reviews[index].user.lower() != currentUser.username.lower():
            raise HTTPException(status_code=403, detail="You can't update others' reviews")
        
        return serviceUpdateReview(title, index, updatedData)
    except HTTPException:
        raise


# delete review

@router.delete("/{title}/review/{index}")
def deleteReview(title: str, index: int, sessionToken: str = Query(...)):
    """Delete a review by index for a specific movie."""
    currentUser = User.getCurrentUser(User, sessionToken)
    if not currentUser:
        raise HTTPException(status_code=401, detail="Login required to Delete Reviews")
    # Use service to fetch movie and validate index consistently with tests
    try:
        movie_obj = getMovieByName(title)
    except HTTPException as e:
        # Propagate movie not found or other errors
        raise e

    if index < 0 or index >= len(movie_obj.reviews):
        raise HTTPException(status_code=404, detail="Review not found")

    review_to_remove = movie_obj.reviews[index]
    # Allow deletion if current user is the creator or is an admin
    if (currentUser.username.lower() != review_to_remove.user.lower()
            and getattr(currentUser, "role", None) != "admin"):
        raise HTTPException(status_code=403, detail="You can't delete others' reviews")

    # Delegate deletion to service layer (repository persistence/memory handled there)
    result = serviceDeleteReview(title, index)
    return result


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
