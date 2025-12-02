import os
import json
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
from backend.schemas.movie import movie
from backend.schemas.movieReviews import movieReviews, movieReviewsCreate, movieReviewsUpdate
from backend.users.user import User
from backend.repositories.itemsRepo import loadReviews
from backend.services.moviesService import (
    addReview as serviceAddReview,
    getMovieByName,
    updateReview as serviceUpdateReview,
    deleteReview as serviceDeleteReview,
)

router = APIRouter()


# add review

# only works if user logs in first, otherwise will not add a review

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
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

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

    try:
        movie_obj = getMovieByName(title)
        if not movie_obj.reviews or index >= len(movie_obj.reviews):
            raise HTTPException(status_code=404, detail="Review not found")
        
        reviewToRemove = movie_obj.reviews[index]
        # Allow deletion if current_user is the creator or is an admin
        if (currentUser.username.lower() != reviewToRemove.user.lower() 
                and getattr(currentUser, "role", None) != "admin"):
            raise HTTPException(status_code=403, detail="You can't delete others' reviews")
        
        return serviceDeleteReview(title, index)
    except HTTPException:
        raise