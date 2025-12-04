import pytest
import json
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch


from backend.routers.movieRouter import router, load_all_movies


app = FastAPI()
app.include_router(router)
client = TestClient(app)

 

# Example Joker metadata used everywhere in tests
JOKER_METADATA = {
    "title": "Joker",
    "movieIMDbRating": 8.4,
    "totalRatingCount": 1213550,
    "totalUserReviews": "11.3K",
    "totalCriticReviews": "697",
    "metaScore": "59",
    "movieGenres": ["Crime", "Drama", "Thriller"],
    "directors": ["Todd Phillips"],
    "datePublished": "2019-10-04",
    "creators": ["Todd Phillips", "Scott Silver", "Bob Kane"],
    "mainStars": ["Joaquin Phoenix", "Robert De Niro", "Zazie Beetz"],
    "description": "A mentally troubled stand-up comedian embarks on a downward spiral that leads to the creation of an iconic villain.",
    "duration": 122,
    "reviews": [],
    "seriesName": None,
    "seriesOrder": None
}


class TestLoadMovies:
    """Tests for load_all_movies() helper + GET / endpoint"""

    def test_load_movies_success(self, tmp_path, monkeypatch):
        """Test loading a valid movie folder with metadata.json"""

        # Create fake directory
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()

        # Create metadata.json
        metadata_file = movie_dir / "metadata.json"
        metadata_file.write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        # Patch DATA_PATH in movieRouter
        monkeypatch.setattr(
            "backend.routers.movieRouter.DATA_PATH",
            str(tmp_path)
        )

        movies = load_all_movies()
        assert len(movies) == 1
        assert movies[0].title == "Joker"

    def test_load_movies_multiple(self, tmp_path, monkeypatch):
        """Test loading multiple movies"""
        for name in ["Joker", "Batman", "Inception"]:
            mdir = tmp_path / name
            mdir.mkdir()
            (mdir / "metadata.json").write_text(
                json.dumps({**JOKER_METADATA, "title": name}),
                encoding="utf-8"
            )

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        movies = load_all_movies()
        assert len(movies) == 3
        titles = [m.title for m in movies]
        assert set(titles) == {"Joker", "Batman", "Inception"}

    def test_load_movies_empty_directory(self, tmp_path, monkeypatch):
        """Empty directory -> load_all_movies returns empty list"""

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        movies = load_all_movies()
        assert movies == []

    def test_get_all_movies_success(self, tmp_path, monkeypatch):
        """GET / should return list of movies"""
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text(
            json.dumps(JOKER_METADATA), encoding="utf-8"
        )

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        response = client.get("/")
        assert response.status_code == 200
        assert response.json()[0]["title"] == "Joker"

    def test_get_all_movies_not_found(self, tmp_path, monkeypatch):
        """If no movie folders exist, return 404"""

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        response = client.get("/")
        assert response.status_code == 404
        assert response.json()["detail"] == "No movies found"

    def test_load_movies_ignore_files_without_metadata(self, tmp_path, monkeypatch):
        """Ignore folders without metadata.json"""

        (tmp_path / "BadFolder").mkdir()  # No metadata.json
        good = tmp_path / "Joker"
        good.mkdir()
        (good / "metadata.json").write_text(
            json.dumps(JOKER_METADATA), encoding="utf-8"
        )

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        movies = load_all_movies()
        assert len(movies) == 1
        assert movies[0].title == "Joker"

class TestGetMovieByTitle:
    """Tests for GET /{title} endpoint"""

    def test_get_movie_success(self, tmp_path, monkeypatch):
        """Retrieve a single movie by title"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text(
            json.dumps(JOKER_METADATA), encoding="utf-8"
        )

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        response = client.get("/Joker")
        assert response.status_code == 200
        assert response.json()["title"] == "Joker"

    def test_get_movie_not_found(self, tmp_path, monkeypatch):
        """If movie folder doesn't exist -> 404"""

        monkeypatch.setattr("backend.routers.movieRouter.DATA_PATH", str(tmp_path))

        response = client.get("/UnknownMovie")
        assert response.status_code == 404
        assert response.json()["detail"] == "Movie 'UnknownMovie' not found"

    # Test removed - movie reviews are now managed through reviewRouter only


DUMMY_REVIEW = {
    "dateOfReview": "2024-01-01",
    "user": "X",
    "usefulnessVote": 0,
    "totalVotes": 0,
    "userRatingOutOf10": 5,
    "reviewTitle": "Test",
    "review": "Test"
}

# Review tests removed - use reviewRouter_test.py for review endpoint tests


class TestSearchMovies:
    """Tests for POST /search endpoint"""

    def test_search_by_title(self, tmp_path, monkeypatch):
        """Search should find movie by partial title match (case-insensitive)"""
        # Create two movies
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        dark_knight_metadata = {
            "title": "The Dark Knight",
            "movieIMDbRating": 9.0,
            "totalRatingCount": 2500000,
            "totalUserReviews": "15K",
            "totalCriticReviews": "800",
            "metaScore": "84",
            "movieGenres": ["Action", "Crime", "Drama"],
            "directors": ["Christopher Nolan"],
            "datePublished": "2008-07-18",
            "creators": ["Jonathan Nolan", "Christopher Nolan"],
            "mainStars": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
            "description": "When the menace known as the Joker wreaks havoc on Gotham.",
            "seriesName": None,
            "seriesOrder": None
        }
        dark_knight_dir = tmp_path / "The Dark Knight"
        dark_knight_dir.mkdir()
        (dark_knight_dir / "metadata.json").write_text(json.dumps(dark_knight_metadata), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Mock TMDB to return no results for pure local testing
        with patch("backend.services.moviesService.search_tmdb", return_value=[]):
            # Search for "joker" - should find both movies (Joker by title, The Dark Knight by description)
            response = client.post("/search", json={"title": "joker"})
            assert response.status_code == 200
            results = response.json()
            assert len(results) == 2
            titles = {r["title"] for r in results}
            assert "Joker" in titles
            assert "The Dark Knight" in titles
    def test_search_by_genre(self, tmp_path, monkeypatch):
        """Search should filter movies by genre"""
        # Create movies with different genres
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        forrest_metadata = {
            "title": "Forrest Gump",
            "movieIMDbRating": 8.8,
            "totalRatingCount": 1900000,
            "totalUserReviews": "12K",
            "totalCriticReviews": "500",
            "metaScore": "82",
            "movieGenres": ["Drama", "Romance"],
            "directors": ["Robert Zemeckis"],
            "datePublished": "1994-07-06",
            "creators": ["Winston Groom", "Eric Roth"],
            "mainStars": ["Tom Hanks", "Robin Wright", "Gary Sinise"],
            "description": "The presidencies of Kennedy and Johnson unfold through the perspective of an Alabama man.",
            "seriesName": None,
            "seriesOrder": None
        }
        forrest_dir = tmp_path / "Forrest Gump"
        forrest_dir.mkdir()
        (forrest_dir / "metadata.json").write_text(json.dumps(forrest_metadata), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Search for "Crime" genre - should only find Joker
        response = client.post("/search", json={"genres": ["Crime"]})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Joker"

        # Search for "Drama" genre - should find both
        response = client.post("/search", json={"genres": ["Drama"]})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        titles = [r["title"] for r in results]
        assert "Joker" in titles
        assert "Forrest Gump" in titles

    def test_search_by_director(self, tmp_path, monkeypatch):
        """Search should filter movies by director"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        response = client.post("/search", json={"directors": ["Todd Phillips"]})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Joker"

    def test_search_by_min_rating(self, tmp_path, monkeypatch):
        """Search should filter movies by minimum rating"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        low_rated_metadata = {
            "title": "Bad Movie",
            "movieIMDbRating": 3.5,
            "totalRatingCount": 1000,
            "totalUserReviews": "100",
            "totalCriticReviews": "50",
            "metaScore": "20",
            "movieGenres": ["Action"],
            "directors": ["Unknown"],
            "datePublished": "2020-01-01",
            "creators": ["Unknown"],
            "mainStars": ["Unknown Actor"],
            "description": "A bad movie.",
            "seriesName": None,
            "seriesOrder": None
        }
        bad_movie_dir = tmp_path / "Bad Movie"
        bad_movie_dir.mkdir()
        (bad_movie_dir / "metadata.json").write_text(json.dumps(low_rated_metadata), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Search for movies with rating >= 8.0
        response = client.post("/search", json={"min_rating": 8.0})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Joker"

    def test_search_by_max_rating(self, tmp_path, monkeypatch):
        """Search should filter movies by maximum rating"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Search for movies with rating <= 5.0 (should find none)
        response = client.post("/search", json={"max_rating": 5.0})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 0

    def test_search_by_year(self, tmp_path, monkeypatch):
        """Search should filter movies by year in datePublished"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Search for movies from 2019
        response = client.post("/search", json={"year": 2019})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Joker"

        # Search for movies from 2020 (should find none)
        response = client.post("/search", json={"year": 2020})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 0

    def test_search_multiple_filters(self, tmp_path, monkeypatch):
        """Search should apply multiple filters together (AND logic)"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        dark_knight_metadata = {
            "title": "The Dark Knight",
            "movieIMDbRating": 9.0,
            "totalRatingCount": 2500000,
            "totalUserReviews": "15K",
            "totalCriticReviews": "800",
            "metaScore": "84",
            "movieGenres": ["Action", "Crime", "Drama"],
            "directors": ["Christopher Nolan"],
            "datePublished": "2008-07-18",
            "creators": ["Jonathan Nolan", "Christopher Nolan"],
            "mainStars": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
            "description": "When the menace known as the Joker wreaks havoc on Gotham.",
            "seriesName": None,
            "seriesOrder": None
        }
        dark_knight_dir = tmp_path / "The Dark Knight"
        dark_knight_dir.mkdir()
        (dark_knight_dir / "metadata.json").write_text(json.dumps(dark_knight_metadata), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        # Search for Crime genre AND min_rating 8.5 - should only find The Dark Knight
        response = client.post("/search", json={"genres": ["Crime"], "min_rating": 8.5})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "The Dark Knight"

    def test_search_empty_filters(self, tmp_path, monkeypatch):
        """Search with no filters should return all movies"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        response = client.post("/search", json={})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Joker"

    def test_search_no_matches(self, tmp_path, monkeypatch):
        """Search with filters that match nothing should return empty list"""
        joker_dir = tmp_path / "Joker"
        joker_dir.mkdir()
        (joker_dir / "metadata.json").write_text(json.dumps(JOKER_METADATA), encoding="utf-8")

        monkeypatch.setattr("backend.services.moviesService.baseDir", tmp_path)

        response = client.post("/search", json={"title": "NonexistentMovie"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 0



