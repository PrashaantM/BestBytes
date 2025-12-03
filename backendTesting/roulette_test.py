import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch

from backend.routers.rouletteRouter import router
from backend.schemas.roulette import RouletteRequest

# Create test app and include roulette router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Dummy movie metadata samples for mocking service layer
MOCK_MOVIES = [
    {
        "title": "Forrest Gump",
        "movieIMDbRating": 8.8,
        "totalRatingCount": "2016919",
        "totalUserReviews": "2.9K",
        "totalCriticReviews": "173",
        "metaScore": "82",
        "movieGenres": ["Drama", "Romance"],
        "directors": ["Robert Zemeckis"],
        "datePublished": "1994-07-06",
        "creators": ["Winston Groom", "Eric Roth"],
        "mainStars": ["Tom Hanks", "Robin Wright", "Gary Sinise"],
        "description": "Great film about life.",
        "duration": 142
    },
    {
        "title": "John Wick Chapter 3 Parabellum",
        "movieIMDbRating": 7.4,
        "totalRatingCount": "330425",
        "totalUserReviews": "2.4K",
        "totalCriticReviews": "399",
        "metaScore": "73",
        "movieGenres": ["Action", "Crime", "Thriller"],
        "directors": ["Chad Stahelski"],
        "datePublished": "2019-07-05",
        "creators": ["Derek Kolstad", "Shay Hatten", "Chris Collins"],
        "mainStars": ["Keanu Reeves", "Halle Berry", "Ian McShane"],
        "description": "World of assassins.",
        "duration": 130
    }
]

@pytest.fixture(autouse=True)
def clear_state():
    """Nothing needed for now but prevents shared mutation later."""
    pass

class TestRouletteGenres:
    def test_get_genres_success(self):
        """GET /roulette/genres returns 200 and contains genres list"""
        res = client.get("/roulette/genres")
        assert res.status_code == 200
        assert "genres" in res.json()

class TestRouletteSpin:
    @patch("backend.services.roulette_service.spin_roulette")
    @patch("backend.services.roulette_service.get_unique_genres")
    def test_spin_no_genre_returns_movie(self, mock_genres, mock_spin):
        """Spin with no genres should still return a movie"""
        mock_spin.return_value = {"movie": MOCK_MOVIES[0], "found": True}
        mock_genres.return_value = ["Action", "Drama", "Crime"]

        res = client.post("/roulette/spin", json={"genres": []})
        assert res.status_code == 200
        data = res.json()
        assert "found" in data
        assert data["found"] is True or data["found"] is False  # response always returns found key
        if data["found"]:
            assert data["movie"]["title"] == "Forrest Gump"

    @patch("backend.services.roulette_service.spin_roulette")
    def test_spin_multiple_genres_filters_correctly(self, mock_spin):
        """Spin roulette matches one of the selected genres"""
        # We'll simulate a John Wick pick
        mock_spin.return_value = {"movie": MOCK_MOVIES[1], "found": True}

        res = client.post("/roulette/spin", json={"genres": ["Action", "Drama"]})
        assert res.status_code == 200
        data = res.json()

        assert data["found"] is True
        # Check if returned movie contains ANY of the selected genres
        assert any(g in ["Action", "Drama"] for g in data["movie"]["movieGenres"])

    @patch("backend.services.roulette_service.spin_roulette")
    def test_spin_no_match_returns_found_false(self, mock_spin):
        """No movie matches selected genres -> found False"""
        mock_spin.return_value = {"movie": {}, "found": False, "message": "No movies found"}

        res = client.post("/roulette/spin", json={"genres": ["Sci-Fi", "Musical"]})
        assert res.status_code == 200
        data = res.json()

        assert data["found"] is False
        assert "message" in data

    @patch("backend.services.roulette_service.spin_roulette")
    def test_spin_returns_full_metadata(self, mock_spin):
        """Spin returns rating, stars, description, duration, etc."""
        mock_spin.return_value = {"movie": MOCK_MOVIES[0], "found": True}

        res = client.post("/roulette/spin", json={"genres": ["Drama"]})
        assert res.status_code == 200
        movie = res.json()["movie"]

        assert "movieIMDbRating" in movie
        assert "mainStars" in movie
        assert "duration" in movie
        assert movie["movieIMDbRating"] == 8.8
        assert movie["duration"] == 142
