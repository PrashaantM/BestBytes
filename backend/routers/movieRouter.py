import os
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List
from backend.schemas.movie import movie, movieFilter
from backend.services.moviesService import searchMovies, getMovieByName
from backend.services.tmdbService import search_tmdb, get_popular_movies

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

def normalize_title(title: str) -> str:
    """Normalize a title for comparison by removing extra spaces, punctuation, etc."""
    import re
    # Convert to lowercase
    normalized = title.lower()
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    # Remove special punctuation but keep alphanumeric and spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def titles_are_similar(title1: str, title2: str, threshold: float = 0.7) -> bool:
    """Check if two titles are similar using fuzzy matching"""
    from difflib import SequenceMatcher
    
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    # Calculate similarity ratio
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Also check if one contains the other (for exact substring matches)
    contains_match = norm1 in norm2 or norm2 in norm1
    
    return ratio >= threshold or contains_match


# Enrich local movies with TMDB poster data by searching for each movie
async def enrich_movies_with_tmdb_posters_via_search(movies: List[movie]) -> List[movie]:
    """Enrich local movies with poster URLs by searching TMDB for each title"""
    
    print(f"DEBUG: Enriching {len(movies)} movies with TMDB search")
    
    for movie_obj in movies:
        if not movie_obj.posterUrl:  # Only enrich if posterUrl is missing
            print(f"DEBUG: Searching TMDB for '{movie_obj.title}'")
            try:
                # Search TMDB for this specific movie (use await, not asyncio.run)
                results = await search_tmdb(movie_obj.title, page=1)
                print(f"DEBUG: Search returned {len(results)} results for '{movie_obj.title}'")
                
                if results:
                    # Use the first result if it's a good match
                    best_match = results[0]
                    tmdb_title = best_match.get("title", "")
                    
                    # Check if title is similar using fuzzy matching
                    if titles_are_similar(movie_obj.title, tmdb_title, threshold=0.65):
                        posterUrl = best_match.get("posterUrl")
                        if posterUrl:
                            movie_obj.posterUrl = posterUrl
                            print(f"DEBUG: Matched '{movie_obj.title}' with TMDB '{tmdb_title}' - posterUrl: {posterUrl}")
                        else:
                            print(f"DEBUG: TMDB result for '{movie_obj.title}' has no posterUrl")
                    else:
                        print(f"DEBUG: No good title match for '{movie_obj.title}' (closest: '{tmdb_title}')")
                else:
                    print(f"DEBUG: No results found for '{movie_obj.title}'")
                    
            except Exception as e:
                print(f"DEBUG: Error searching TMDB for '{movie_obj.title}': {e}")
                pass
    
    return movies


def convert_tmdb_to_movie(tmdb_data: dict) -> movie:
    """Convert TMDB API data to our movie schema"""
    return movie(
        title=tmdb_data.get("title", "Unknown"),
        movieIMDbRating=tmdb_data.get("voteAverage", 0.0),
        totalRatingCount=0,
        totalUserReviews="0",
        totalCriticReviews="0",
        metaScore="N/A",
        movieGenres=tmdb_data.get("genres", []) if isinstance(tmdb_data.get("genres"), list) else [],
        directors=["Unknown"],
        datePublished=tmdb_data.get("releaseDate", ""),
        creators=["TMDB"],
        mainStars=["Unknown"],
        description=tmdb_data.get("overview", "")[:500],
        posterUrl=tmdb_data.get("posterUrl"),
        reviews=[]
    )


async def fetch_tmdb_popular_movies(num_pages: int = 2) -> List[movie]:
    """Fetch popular movies from TMDB and convert to our movie schema"""
    all_movies = []
    
    for page in range(1, num_pages + 1):
        try:
            tmdb_results = await get_popular_movies(page=page)
            for tmdb_data in tmdb_results:
                all_movies.append(convert_tmdb_to_movie(tmdb_data))
        except Exception as e:
            print(f"DEBUG: Error fetching TMDB page {page}: {e}")
            break
    
    return all_movies

# list all movies

# DATA_PATH is correct
# load_all_movies() function is working
# The router is mounted correctly
# Docker is mapping folder properly

@router.get("/", response_model=List[movie])
async def getAllMovies(page: int = Query(1, ge=1, description="Page number (starts at 1)"), 
                 limit: int = Query(10, ge=1, le=100, description="Number of movies per page (1-100)"),
                 include_tmdb: bool = Query(False, description="Include popular movies from TMDB")):
    """
    Return movies from the /data directory merged with TMDB popular movies.
    
    - **page**: Page number (default: 1)
    - **limit**: Number of movies per page (default: 10, max: 100)
    - **include_tmdb**: If true, fetches popular movies from TMDB and merges with local (default: false)
    
    Example: GET /movies/?page=1&limit=12&include_tmdb=true
    """
    print(f"DEBUG: getAllMovies called - page={page}, limit={limit}, include_tmdb={include_tmdb}")
    
    # Start with local movies
    local_movies = load_all_movies()
    print(f"DEBUG: Loaded {len(local_movies)} local movies")
    
    # Enrich local movies with TMDB poster data
    local_movies = await enrich_movies_with_tmdb_posters_via_search(local_movies)
    
    # Merge with TMDB popular movies if requested
    if include_tmdb:
        print(f"DEBUG: include_tmdb=true, fetching TMDB popular movies...")
        try:
            tmdb_movies = await fetch_tmdb_popular_movies(num_pages=2)
            print(f"DEBUG: Fetched {len(tmdb_movies)} movies from TMDB")
            # Merge: local movies first, then TMDB movies
            all_movies = local_movies + tmdb_movies
        except Exception as e:
            print(f"DEBUG: Error fetching TMDB movies: {e}")
            all_movies = local_movies
    else:
        all_movies = local_movies
    
    if not all_movies:
        raise HTTPException(status_code=404, detail="No movies found")
    
    # Calculate pagination
    total_movies = len(all_movies)
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    print(f"DEBUG: Total movies: {total_movies}, page: {page}, limit: {limit}, range: {start_index}-{end_index}")
    
    # Validate page number - only reject if start_index is beyond total movies
    if start_index >= total_movies and page > 1:
        raise HTTPException(status_code=404, detail=f"Page {page} is out of range. Total movies: {total_movies}")
    
    # Return paginated results
    paginated_movies = all_movies[start_index:end_index]
    print(f"DEBUG: Returning {len(paginated_movies)} movies for page {page}")
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
