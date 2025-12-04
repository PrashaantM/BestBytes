from fastapi import APIRouter, HTTPException
from typing import List, Tuple, Dict

from backend.services.seriesService import (
    listAllSeries,
    createSeries,
    updateSeries,
    deleteSeries,
    getMoviesInSeries,
    validateSeriesOrders
)
from backend.users.user import User
from backend.routers.listsRouter import userMovieLists

router = APIRouter()


def verifyUser(sessionToken: str):
    user = User.getCurrentUser(sessionToken)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return user


@router.get("/")
def get_all_series() -> Dict[str, List[Dict]]:
    return listAllSeries()


@router.get("/{seriesName}")
def get_series_movies(seriesName: str):
    movies = getMoviesInSeries(seriesName)
    if not movies:
        raise HTTPException(status_code=404, detail=f"No movies found in series '{seriesName}'")
    return movies


@router.post("/create")
def create_series_api(
    seriesName: str,
    movies: List[Tuple[str, int]],
    sessionToken: str
):
    user = verifyUser(sessionToken)

    # only admins can do this
    if not user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    validateSeriesOrders(movies)
    createSeries(seriesName, movies)

    return {"message": f"Series '{seriesName}' created successfully"}


@router.put("/update/{seriesName}")
def update_series_api(
    seriesName: str,
    movies: List[Tuple[str, int]],
    sessionToken: str
):
    user = verifyUser(sessionToken)

    if not user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    validateSeriesOrders(movies)
    updateSeries(seriesName, movies)

    return {"message": f"Series '{seriesName}' updated successfully"}


@router.delete("/{seriesName}")
def delete_series_api(seriesName: str, sessionToken: str):
    user = verifyUser(sessionToken)

    if not user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return deleteSeries(seriesName)


@router.get("/{seriesName}/progress/{username}")
def get_series_progress(seriesName: str, username: str, sessionToken: str):
    """Return how many movies from the series the user has watched."""

    current_user = User.getCurrentUser(sessionToken)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    series_movies = getMoviesInSeries(seriesName)
    if not series_movies:
        raise HTTPException(status_code=404, detail=f"Series '{seriesName}' not found")

    username_key = username.lower()
    if username_key not in userMovieLists:
        raise HTTPException(status_code=404, detail="User has no lists")

    watched_list = userMovieLists[username_key].get("watched", [])

    series_titles = [m.title for m in series_movies]

    watched_count = sum(1 for title in series_titles if title in watched_list)
    total_movies = len(series_titles)

    progress_percent = (watched_count / total_movies) * 100 if total_movies > 0 else 0

    return {
        "seriesName": seriesName,
        "totalMovies": total_movies,
        "watched": watched_count,
        "progressPercent": round(progress_percent, 2)
    }