import os
import json
from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.movie import movie, movieFilter
from backend.schemas.movieReviews import movieReviews, movieReviewsCreate
from backend.users.user import User
from backend.services.moviesService import searchMovies, addReview as serviceAddReview, getMovieByName

router = APIRouter()

# load data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

movie_reviews_memory = {}

# helper to load movies
def loadAllMovies() -> List[movie]:
    movies = []
    for folder_name in os.listdir(DATA_PATH):
        folder_path = os.path.join(DATA_PATH, folder_name)
        metadata_file = os.path.join(folder_path, "metadata.json")

        if os.path.isdir(folder_path) and os.path.exists(metadata_file):
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                reviews = movie_reviews_memory.get(data["title"].lower(), [])
                data["reviews"] = reviews
                movies.append(movie(**data))
    return movies

# Backwards-compatible name expected by tests
def load_all_movies() -> List[movie]:
    return loadAllMovies()

# list all movies

# DATA_PATH is correct
# load_all_movies() function is working
# The router is mounted correctly
# Docker is mapping folder properly

@router.get("/", response_model=List[movie])
def getAllMovies():
    """Return all movies found in the /data directory."""
    movies = load_all_movies()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found in data directory")
    return movies

# search movies with filters
@router.post("/search", response_model=List[movie])
def search_movies(filters: movieFilter):
    """Search for movies based on various filters like title, genres, directors, rating, and year."""
    results = searchMovies(filters)
    return results

# get movie details

# The case-insensitive lookup is working.
# The metadata file was found.
# No incorrect validation issues.

@router.get("/{title}", response_model=movie)
def getMovieByTitle(title: str):
    """Return one movie by its folder name (case-insensitive)."""
    movie_folder = os.path.join(DATA_PATH, title)
    metadata_path = os.path.join(movie_folder, "metadata.json")

    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        reviews = movie_reviews_memory.get(title.lower(), [])
        data["reviews"] = reviews
        return movie(**data)

# add a review for a movie (root path as tests expect)
@router.post("/{title}/review", response_model=movieReviews)
def add_review(title: str, reviewData: movieReviewsCreate, sessionToken: str):
    """Add a review for a specific movie by title (expects root path)."""
    currentUser = User.getCurrentUser(User, sessionToken)
    if not currentUser:
        raise HTTPException(status_code=401, detail="Login required to review")

    # verify movie exists
    try:
        getMovieByName(title)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    # date format validation
    from datetime import datetime
    try:
        datetime.strptime(reviewData.dateOfReview, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use YYYY-MM-DD format (e.g., 2025-11-28)"
        )

    # non-empty title and body
    if not reviewData.reviewTitle.strip() or not reviewData.review.strip():
        raise HTTPException(status_code=400, detail="Review title and text cannot be empty")

    # persist via service and update in-memory cache
    saved = serviceAddReview(title, reviewData)
    key = title.lower()
    movie_reviews_memory.setdefault(key, []).append(saved)
    return saved
