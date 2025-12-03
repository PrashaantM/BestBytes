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