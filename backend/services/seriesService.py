from pathlib import Path
from typing import Dict, List, Tuple
from fastapi import HTTPException

from repositories.itemsRepo import loadMetadata, saveMetadata, loadReviews
from schemas.movie import movie

baseDir = Path(__file__).resolve().parents[1] / "data"


# lists all series in the system
def listAllSeries() -> Dict[str, List[Dict]]:
    """
    Scan all movie metadata and return a dictionary:

    {
        "John Wick": [
            {"title": "John Wick", "order": 1},
            {"title": "John Wick 2", "order": 2}
        ],
        "Avengers": [...]
    }
    """
    if not baseDir.exists():
        return {}

    seriesMap: Dict[str, List[Dict]] = {}

    for movieFolder in baseDir.iterdir():
        if not movieFolder.is_dir():
            continue

        metadata = loadMetadata(movieFolder.name)
        if not metadata:
            continue

        seriesName = metadata.get("seriesName")
        seriesOrder = metadata.get("seriesOrder")

        if not seriesName:
            continue  # standalone movie

        seriesMap.setdefault(seriesName, [])
        seriesMap[seriesName].append({
            "title": metadata["title"],
            "order": seriesOrder
        })

    # sorts by movie order within series
    for name in seriesMap:
        seriesMap[name].sort(key=lambda x: (x["order"] is None, x["order"]))

    return seriesMap


# creates series for exisitng movies in the db
def createSeries(seriesName: str, movies: List[Tuple[str, int]]):
    """
    Create a new series by assigning multiple existing movies to it.

    movies → list of (movieTitle, seriesOrder)

    Example:
    createSeries("John Wick Saga", [
        ("John Wick", 1),
        ("John Wick 2", 2),
        ("John Wick 3", 3)
    ])
    """

    for (title, order) in movies:
        metadata = loadMetadata(title)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Movie '{title}' does not exist")

        metadata["seriesName"] = seriesName
        metadata["seriesOrder"] = order

        saveMetadata(title, metadata)


# updates existing series
def updateSeries(seriesName: str, movies: List[Tuple[str, int]]):
    """
    Update an existing series with a new list of movies and orders.
    Old movies in the series will be removed.
    """

    for movieFolder in baseDir.iterdir():
        if not movieFolder.is_dir():
            continue

        metadata = loadMetadata(movieFolder.name)
        if metadata and metadata.get("seriesName") == seriesName:
            metadata["seriesName"] = None
            metadata["seriesOrder"] = None
            saveMetadata(movieFolder.name, metadata)

    createSeries(seriesName, movies)


# delete series
def deleteSeries(seriesName: str):
    """
    Remove seriesName and seriesOrder from all movies in that series.
    """
    found = False

    for movieFolder in baseDir.iterdir():
        if not movieFolder.is_dir():
            continue

        metadata = loadMetadata(movieFolder.name)
        if metadata and metadata.get("seriesName") == seriesName:
            found = True
            metadata["seriesName"] = None
            metadata["seriesOrder"] = None
            saveMetadata(movieFolder.name, metadata)

    if not found:
        raise HTTPException(status_code=404, detail=f"Series '{seriesName}' not found")

    return {"message": f"Series '{seriesName}' deleted successfully"}


# get all movies in a series
def getMoviesInSeries(seriesName: str) -> List[movie]:
    """
    Return a sorted list of movie objects belonging to a series.
    """
    if not baseDir.exists():
        return []

    result = []

    for movieFolder in baseDir.iterdir():
        if not movieFolder.is_dir():
            continue

        metadata = loadMetadata(movieFolder.name)
        if metadata and metadata.get("seriesName") == seriesName:
            reviews = loadReviews(movieFolder.name)
            result.append(movie(**metadata, reviews=reviews))

    result.sort(key=lambda m: (m.seriesOrder is None, m.seriesOrder))
    return result


# validate the order of movies ina series
def validateSeriesOrders(movies: List[Tuple[str, int]]):
    """
    Ensures:
      - No duplicate orders
      - All orders are positive integers
    """

    orders = [order for (_, order) in movies]

    if len(orders) != len(set(orders)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate seriesOrder values are not allowed"
        )

    for order in orders:
        if not isinstance(order, int) or order <= 0:
            raise HTTPException(
                status_code=400,
                detail="seriesOrder must be a positive integer"
            )