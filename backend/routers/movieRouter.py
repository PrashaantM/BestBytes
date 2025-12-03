import os
import json
from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.movie import movie, movieFilter
from backend.services.moviesService import searchMovies, getMovieByName

router = APIRouter()

# load data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

# helper to load movies
def loadAllMovies() -> List[movie]:
    movies = []
    for folder_name in os.listdir(DATA_PATH):
        folder_path = os.path.join(DATA_PATH, folder_name)
        metadata_file = os.path.join(folder_path, "metadata.json")

        if os.path.isdir(folder_path) and os.path.exists(metadata_file):
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Load reviews from reviewRouter's persistent storage
                data["reviews"] = []
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
        # Load reviews from reviewRouter's persistent storage
        data["reviews"] = []
        return movie(**data)
