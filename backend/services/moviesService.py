import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from typing import List, Dict
from fastapi import HTTPException
import json
import asyncio

from schemas.movie import movie, movieCreate, movieUpdate, movieFilter
from schemas.movieReviews import movieReviews, movieReviewsCreate, movieReviewsUpdate
from repositories.itemsRepo import loadMetadata, loadReviews, saveMetadata, saveReviews
from users import user
from .tmdbService import search_tmdb, get_tmdb_movie_details

baseDir = Path(__file__).resolve().parents[1] / "data" # basDir is now pointing to data folder 

#creates a movies list and adds reviews to each 
def listMovies() -> List[movie]:
    if not baseDir.exists(): #checks if data folder exists
        return []
    movies: List[movie] = [] #will hold movie objects
    for movieFolder in baseDir.iterdir(): #returns iterator over all items in data/
        if movieFolder.is_dir():
            metadata = loadMetadata(movieFolder.name)
            reviews = loadReviews(movieFolder.name)
            if metadata:
                movies.append(movie(**metadata, reviews=reviews))
                print(f"Loaded movie: {movieFolder.name} -> {movies[-1]}")
    return movies

def getMovieByName(title: str) -> movie:
    movieDir = baseDir / title #create /data/movie name dir
    if not movieDir.exists(): # checls if movieDir exists
        raise HTTPException(status_code = 404, detail = "Movie {Title} not found")


    metadata = loadMetadata(title)
    reviews = loadReviews(title)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"No metadata for {title}")
    
    return movie(**metadata, reviews = reviews)

def createMovie(payload: movieCreate) -> movie:
    movieDir = baseDir / payload.title #creates path for new movie title
    if movieDir.exists():
        raise HTTPException(status_code=409, detail=f"Movie {payload.title} already exists")
    
    saveMetadata(payload.title, payload.dict()) #creates movie folder if it doesnt exists and metadata.json
    saveReviews(payload.title,[])#creates Moviereviews.csv
    return movie(**payload.dict(), reviews = [])

def updateMovie(title: str, payload: movieUpdate) -> movie:
    """Update an existing movie's metadata."""
    movieDir = baseDir / title
    if not movieDir.exists():
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    saveMetadata(title, payload.dict())
    reviews = loadReviews(title)
    return movie(**payload.dict(), reviews=reviews)


def deleteMovie(title: str) -> None:
    """Delete a movie folder and all its files."""
    movieDir = baseDir / title
    if not movieDir.exists():
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    for file in movieDir.iterdir():
        file.unlink()
    movieDir.rmdir()


def addReview(title: str, payload: movieReviewsCreate) -> movieReviews:
    """Add a review to a movie's CSV file."""
    movieDir = baseDir / title
    if not movieDir.exists():
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    reviews = loadReviews(title)
    newReview = payload.dict()
    reviews.append(newReview)
    saveReviews(title, reviews)
    return movieReviews(**newReview)


def updateReview(title: str, index: int, payload: movieReviewsUpdate) -> movieReviews:
    """Update an existing review by index for a specific movie."""
    movieDir = baseDir / title
    if not movieDir.exists():
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    reviews = loadReviews(title)
    if not reviews or index >= len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")

    # Update the review at the given index
    updatedReviewData = {**reviews[index], **payload.dict(exclude_unset=True)}
    reviews[index] = updatedReviewData
    saveReviews(title, reviews)
    return movieReviews(**updatedReviewData)


def deleteReview(title: str, index: int) -> dict:
    """Delete a review by index for a specific movie."""
    movieDir = baseDir / title
    if not movieDir.exists():
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    reviews = loadReviews(title)
    if not reviews or index >= len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")

    removed = reviews.pop(index)
    saveReviews(title, reviews)
    return {"message": f"Deleted review '{removed.get('reviewTitle', 'Unknown')}' by {removed.get('user', 'Unknown')}"}


def searchMovies(filters: movieFilter) -> List[movie]:
    """Filter movies based on local metadata and optionally augment with TMDB results."""
    if not baseDir.exists():
        return []

    results: List[movie] = []

    for movieFolder in baseDir.iterdir():
        if not movieFolder.is_dir(): #iterates through list
            continue

        metadata = loadMetadata(movieFolder.name)
        if not metadata:
            continue

        # Build movie object without reviews
        m = movie(**{k: v for k, v in metadata.items() if k != "reviews"}, reviews=[]) #creates movie object without reviews
        include = True#included in list until proven otherwise

        # --- Title ---
        if filters.title and filters.title.lower() not in m.title.lower():#checks if title exists of if it's a substring
            include = False

        # --- Genres ---
        if getattr(filters, "genres", None):
            if not any(
                g.lower() in [mg.lower() for mg in m.movieGenres] for g in filters.genres #list all movie genres, then check if any filter movie genres match
            ):
                include = False

        # --- Directors ---
        if getattr(filters, "directors", None):
            if not any(
                d.lower() in [md.lower() for md in m.directors] for d in filters.directors
            ):
                include = False

        # --- IMDb Rating ---
        if filters.min_rating is not None and m.movieIMDbRating < filters.min_rating:
            include = False
        if filters.max_rating is not None and m.movieIMDbRating > filters.max_rating:
            include = False

        # --- Year ---
        if filters.year and str(filters.year) not in m.datePublished:
            include = False

        if include:
            results.append(m)

    # If title provided, also search TMDB and merge minimal results
    try:
        if filters.title:
            tmdb_items: List[Dict] = asyncio.run(search_tmdb(filters.title, 1))
            for t in tmdb_items:
                try:
                    mapped = movie(
                        title=t.get("title") or "",
                        movieIMDbRating=float(t.get("voteAverage") or 0.0),
                        totalRatingCount=0,
                        totalUserReviews="0",
                        totalCriticReviews="0",
                        metaScore="",
                        movieGenres=[],
                        directors=[],
                        datePublished=(t.get("releaseDate") or ""),
                        creators=[],
                        mainStars=[],
                        description="",
                        reviews=[],
                        posterUrl=t.get("posterUrl"),
                        trailerUrl=t.get("trailerUrl")
                    )
                    # Avoid duplicate titles (case-insensitive)
                    if not any(m.title.lower() == mapped.title.lower() for m in results):
                        results.append(mapped)
                except Exception:
                    continue
    except Exception:
        # If TMDB fails, return local results only
        pass

    return results

def saveMovieList(list : List[movie], user: str, listName: str, path: Path):
    data = {}
    path.mkdir(parents= True, exist_ok= True)
    path = path/"movieLists.json"

    if path.exists():
        with open(path,'r+') as jsonFile:
            try:
                data = json.load(jsonFile)
            except json.JSONDecodeError:
                 data = {}
            jsonFile.close()
    
    if user not in data:
        data[user] = {}

    data[user][listName] = list

    with open(path, 'w') as jsonFile:
        json.dump(data,jsonFile)
        jsonFile.close()


async def importTmdbMovieByTitle(title: str) -> movie:
    """
    Search TMDB for a movie by title and import the first match to local storage.
    Creates the movie folder, metadata.json, and empty reviews CSV.
    Returns the created movie object.
    Raises HTTPException if movie not found in TMDB.
    """
    # Search TMDB for the movie
    tmdb_results = await search_tmdb(title, page=1)
    
    if not tmdb_results:
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found in TMDB")
    
    # Get the first result (best match)
    first_result = tmdb_results[0]
    tmdb_id = first_result.get("id")
    
    # Fetch full details including trailer
    details = await get_tmdb_movie_details(tmdb_id)
    
    # Map TMDB data to our movie schema
    movie_data = {
        "title": details.get("title", title),
        "movieIMDbRating": details.get("voteAverage", 0.0),
        "totalRatingCount": 0,
        "totalUserReviews": "0",
        "totalCriticReviews": "0",
        "metaScore": "",
        "movieGenres": details.get("genres", []),
        "directors": [],
        "datePublished": details.get("releaseDate", ""),
        "creators": [],
        "mainStars": [],
        "description": details.get("overview", ""),
        "posterUrl": details.get("posterUrl"),
        "trailerUrl": details.get("trailerUrl"),
        "seriesName": None, 
        "seriesOrder": None,
    }
    
    # Create the movie locally
    movie_create = movieCreate(**movie_data)
    saveMetadata(movie_create.title, movie_create.model_dump())
    saveReviews(movie_create.title, [])
    
    return movie(**movie_data, reviews=[])


def importTmdbMovieByTitleSync(title: str) -> movie:
    """
    Synchronous wrapper for importTmdbMovieByTitle.
    Used in contexts where async/await is not available.
    """
    return asyncio.run(importTmdbMovieByTitle(title))


def getOrImportMovie(title: str) -> movie:
    """
    Get a movie by title from local storage, or import from TMDB if not found.
    Returns the movie object.
    Raises HTTPException if movie not found locally or in TMDB.
    """
    movieDir = baseDir / title
    
    # If movie exists locally, return it
    if movieDir.exists():
        metadata = loadMetadata(title)
        reviews = loadReviews(title)
        if metadata:
            return movie(**metadata, reviews=reviews)
    
    # Movie doesn't exist locally, try to import from TMDB
    try:
        return importTmdbMovieByTitleSync(title)
    except HTTPException:
        # Re-raise with appropriate message
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found locally or in TMDB")


def setMovieSeries(movieTitle: str, seriesName: str, seriesOrder: int) -> movie:
    """
    Assign a movie to a series with a specific order.
    """
    metadata = loadMetadata(movieTitle)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Movie '{movieTitle}' not found")

    metadata["seriesName"] = seriesName
    metadata["seriesOrder"] = seriesOrder

    saveMetadata(movieTitle, metadata)
    reviews = loadReviews(movieTitle)

    return movie(**metadata, reviews=reviews)


def getSeriesOfMovie(movieTitle: str) -> Dict:
    """
    Return the seriesName and seriesOrder of a movie.
    """
    metadata = loadMetadata(movieTitle)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Movie '{movieTitle}' not found")

    return {
        "seriesName": metadata.get("seriesName"),
        "seriesOrder": metadata.get("seriesOrder")
    }


def getMoviesInSeries(seriesName: str) -> List[movie]:
    """
    Return all movies that belong to the given series, sorted by seriesOrder.
    """
    if not baseDir.exists():
        return []

    result = []
    for movieFolder in baseDir.iterdir():
        if movieFolder.is_dir():
            metadata = loadMetadata(movieFolder.name)
            if metadata and metadata.get("seriesName") == seriesName:
                reviews = loadReviews(movieFolder.name)
                result.append(movie(**metadata, reviews=reviews))

    # Sort by order, put None last
    result.sort(key=lambda m: (m.seriesOrder is None, m.seriesOrder))
    return result

    





