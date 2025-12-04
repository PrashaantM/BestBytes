import pytest
from pathlib import Path
from fastapi import HTTPException

import backend.services.seriesService as seriesService


@pytest.fixture
def tempDir(tmp_path, monkeypatch):
    """
    Patches seriesService.baseDir → tmp_path.
    Every movie folder will be created inside tmp_path.
    """
    monkeypatch.setattr(seriesService, "baseDir", tmp_path)
    return tmp_path


def create_movie(tmp, title, metadata):
    movie_dir = tmp / title
    movie_dir.mkdir()
    (movie_dir / "metadata.json").write_text(
        seriesService.saveMetadata.__wrapped__(title, metadata)
        if hasattr(seriesService.saveMetadata, "__wrapped__")
        else metadata.__repr__(),  # overwritten later through monkeypatch
        encoding="utf-8"
    )
    return movie_dir


@pytest.fixture
def patch_repo(monkeypatch, tmp_path):
    """
    Patch loadMetadata, saveMetadata, loadReviews so we can store metadata in memory.
    """
    storage = {}

    def fake_load(title):
        return storage.get(title)

    def fake_save(title, meta):
        storage[title] = meta

    def fake_reviews(title):
        return []

    monkeypatch.setattr(seriesService, "loadMetadata", fake_load)
    monkeypatch.setattr(seriesService, "saveMetadata", fake_save)
    monkeypatch.setattr(seriesService, "loadReviews", fake_reviews)

    return storage


# lists all series
def test_list_all_series(tempDir, patch_repo):
    storage = patch_repo
    # create movies with metadata
    storage["Movie1"] = {"title": "Movie1", "seriesName": "Saga", "seriesOrder": 2}
    storage["Movie2"] = {"title": "Movie2", "seriesName": "Saga", "seriesOrder": 1}
    storage["StandAlone"] = {"title": "StandAlone", "seriesName": None}

    (tempDir / "Movie1").mkdir()
    (tempDir / "Movie2").mkdir()
    (tempDir / "StandAlone").mkdir()

    result = seriesService.listAllSeries()
    assert "Saga" in result
    assert result["Saga"][0]["title"] == "Movie2"
    assert result["Saga"][1]["title"] == "Movie1"


# create series
def test_create_series_success(tempDir, patch_repo):
    storage = patch_repo
    storage["A"] = {"title": "A"}
    storage["B"] = {"title": "B"}

    (tempDir / "A").mkdir()
    (tempDir / "B").mkdir()

    seriesService.createSeries("MySeries", [("A", 1), ("B", 2)])

    assert storage["A"]["seriesName"] == "MySeries"
    assert storage["A"]["seriesOrder"] == 1
    assert storage["B"]["seriesOrder"] == 2


def test_create_series_nonexistent_movie(tempDir, patch_repo):
    storage = patch_repo
    storage["A"] = {"title": "A"}

    (tempDir / "A").mkdir()

    with pytest.raises(HTTPException) as e:
        seriesService.createSeries("X", [("A", 1), ("Missing", 2)])

    assert e.value.status_code == 404


# update series
def test_update_series(tempDir, patch_repo):
    storage = patch_repo

    # existing series
    storage["M1"] = {"title": "M1", "seriesName": "Old", "seriesOrder": 1}
    storage["M2"] = {"title": "M2", "seriesName": "Old", "seriesOrder": 2}

    # new movies
    storage["New1"] = {"title": "New1"}
    storage["New2"] = {"title": "New2"}

    for name in ["M1", "M2", "New1", "New2"]:
        (tempDir / name).mkdir()

    seriesService.updateSeries("Old", [("New1", 10), ("New2", 20)])

    # old series removed
    assert storage["M1"]["seriesName"] is None
    assert storage["M2"]["seriesName"] is None

    # new series added
    assert storage["New1"]["seriesOrder"] == 10
    assert storage["New2"]["seriesOrder"] == 20


# delete series
def test_delete_series_success(tempDir, patch_repo):
    storage = patch_repo

    storage["X1"] = {"title": "X1", "seriesName": "Saga"}
    storage["X2"] = {"title": "X2", "seriesName": "Saga"}

    (tempDir / "X1").mkdir()
    (tempDir / "X2").mkdir()

    resp = seriesService.deleteSeries("Saga")

    assert resp == {"message": "Series 'Saga' deleted successfully"}
    assert storage["X1"]["seriesName"] is None
    assert storage["X2"]["seriesOrder"] is None


def test_delete_series_not_found(tempDir, patch_repo):
    storage = patch_repo
    storage["A"] = {"title": "A", "seriesName": None}
    (tempDir / "A").mkdir()

    with pytest.raises(HTTPException):
        seriesService.deleteSeries("NotThere")


# get movies in the series
def test_get_movies_in_series(tempDir, patch_repo):
    storage = patch_repo

    fullMeta1 = {
        "title": "M1",
        "seriesName": "Saga",
        "seriesOrder": 2,
        "movieIMDbRating": 8.0,
        "totalRatingCount": 100,
        "totalUserReviews": "50",
        "totalCriticReviews": "10",
        "metaScore": "70",
        "movieGenres": ["Action"],
        "movieRuntime": "120 min",
        "directors": ["Director One"],
        "creators": ["Creator One"],
        "mainStars": ["Actor A"],
        "description": "Desc",
        "datePublished": "2020-01-01"
    }

    fullMeta2 = {
        "title": "M2",
        "seriesName": "Saga",
        "seriesOrder": 1,
        "movieIMDbRating": 9.0,
        "totalRatingCount": 200,
        "totalUserReviews": "80",
        "totalCriticReviews": "20",
        "metaScore": "80",
        "movieGenres": ["Adventure"],
        "movieRuntime": "110 min",
        "directors": ["Director Two"],
        "creators": ["Creator Two"],
        "mainStars": ["Actor B"],
        "description": "Desc2",
        "datePublished": "2021-01-01"
    }

    storage["M1"] = fullMeta1
    storage["M2"] = fullMeta2

    (tempDir / "M1").mkdir()
    (tempDir / "M2").mkdir()

    movies = seriesService.getMoviesInSeries("Saga")

    assert len(movies) == 2
    # sorted
    assert movies[0].title == "M2"
    assert movies[1].title == "M1"



def test_get_movies_in_series_empty(tempDir, patch_repo):
    storage = patch_repo

    storage["A"] = {"title": "A", "seriesName": None}
    (tempDir / "A").mkdir()

    result = seriesService.getMoviesInSeries("Unknown")
    assert result == []


# validate series order
def test_validate_orders_success():
    seriesService.validateSeriesOrders([("A", 1), ("B", 2)])


def test_validate_orders_duplicate():
    with pytest.raises(HTTPException) as e:
        seriesService.validateSeriesOrders([("A", 1), ("B", 1)])
    assert e.value.status_code == 400


def test_validate_orders_invalid():
    with pytest.raises(HTTPException):
        seriesService.validateSeriesOrders([("A", -1)])
