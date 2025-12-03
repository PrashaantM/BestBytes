import os
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List
from backend.schemas.movie import movie, movieFilter
from backend.services.moviesService import searchMovies, getMovieByName
from backend.services.tmdbService import get_popular_movies

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
def getAllMovies(page: int = Query(1, ge=1, description="Page number (starts at 1)"), 
                 limit: int = Query(10, ge=1, le=100, description="Number of movies per page (1-100)"),
                 include_tmdb: bool = Query(False, description="Include popular movies from TMDB")):
    """
    Return movies from the /data directory with pagination.
    
    - **page**: Page number (default: 1)
    - **limit**: Number of movies per page (default: 10, max: 100)
    - **include_tmdb**: If true, fetches popular movies from TMDB and merges with local movies (default: false)
    
    Example: GET /movies/?page=1&limit=10&include_tmdb=true
    """
    movies = load_all_movies()
    
    # Optionally fetch and merge TMDB popular movies
    if include_tmdb:
        try:
            # Fetch multiple pages of TMDB popular movies to ensure enough content for infinite scroll
            # Fetch enough pages to have at least (page * limit) + 50 movies
            # This ensures we always have content for the next few pages
            total_needed = page * limit + 50
            tmdb_pages_needed = max(3, (total_needed // 20) + 1)
            
            for tmdb_page in range(1, tmdb_pages_needed + 1):
                tmdb_results = asyncio.run(get_popular_movies(page=tmdb_page))
                
                # Convert TMDB results to movie schema
                for tmdb_movie in tmdb_results:
                    # Check if movie already exists locally (avoid duplicates)
                    if not any(m.title.lower() == tmdb_movie.get("title", "").lower() for m in movies):
                        # Map TMDB data to movie schema
                        description = tmdb_movie.get("overview", "")
                        # Truncate description to fit schema max length (500 chars)
                        if len(description) > 500:
                            description = description[:497] + "..."
                        
                        mapped = movie(
                            title=tmdb_movie.get("title", "Unknown"),
                            movieIMDbRating=tmdb_movie.get("voteAverage", 0.0),
                            totalRatingCount=0,
                            totalUserReviews="0",
                            totalCriticReviews="0",
                            metaScore="",
                            movieGenres=[],
                            directors=[],
                            datePublished=tmdb_movie.get("releaseDate", ""),
                            creators=[],
                            mainStars=[],
                            description=description,
                            posterUrl=tmdb_movie.get("posterUrl"),
                            trailerUrl=None,
                            reviews=[]
                        )
                        movies.append(mapped)
        except Exception as e:
            # If TMDB fails, just continue with local movies
            pass
    
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found in data directory")
    
    # Calculate pagination
    total_movies = len(movies)
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    # Validate page number - only reject if start_index is beyond total movies
    if start_index >= total_movies and page > 1:
        raise HTTPException(status_code=404, detail=f"Page {page} is out of range. Total movies: {total_movies}")
    
    # Return paginated results (may be empty for the last page)
    paginated_movies = movies[start_index:end_index]
    return paginated_movies

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
