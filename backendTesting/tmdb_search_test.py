import json
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.app import app

# Mock TMDB_API_KEY for all tests in this file
os.environ.setdefault("TMDB_API_KEY", "test_api_key_for_testing")

client = TestClient(app)

fake_tmdb_results = [
    {
        "id": 155,
        "title": "Inception",  # Different from local data to test TMDB merge
        "releaseDate": "2010-07-16",
        "voteAverage": 8.8,
        "overview": "A thief who steals secrets through dreams.",
        "posterUrl": "https://image.tmdb.org/t/p/w500/inception.jpg",
        "trailerUrl": None,
    },
]

@patch("backend.services.moviesService.search_tmdb", new_callable=AsyncMock)
def test_unified_search_includes_tmdb_with_poster(mock_search_tmdb):
    """Verify unified search merges TMDB results with posterUrl and trailerUrl fields"""
    # Configure the AsyncMock to return fake results when awaited
    mock_search_tmdb.return_value = fake_tmdb_results

    resp = client.post(
        "/movies/search",
        json={"title": "inception"}
    )
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify mock was called
    mock_search_tmdb.assert_called_once_with("inception", 1)
    
    # Find TMDB item (should be unique since not in local DB)
    found = next((m for m in data if m.get("title") == "Inception"), None)
    assert found is not None, "TMDB result should be included in search"
    
    # Verify camelCase fields exist
    assert "posterUrl" in found
    assert "trailerUrl" in found
    
    # Verify values (posterUrl should be preserved from TMDB service)
    assert found["posterUrl"] == "https://image.tmdb.org/t/p/w500/inception.jpg"
    assert found["trailerUrl"] is None


def test_local_movie_has_optional_fields():
    """Verify local movies include the optional posterUrl and trailerUrl fields (as None)"""
    resp = client.post(
        "/movies/search",
        json={"title": "Joker"}
    )
    assert resp.status_code == 200
    data = resp.json()
    
    joker = next((m for m in data if "Joker" in m.get("title", "")), None)
    assert joker is not None
    
    # Fields should exist even if None for local movies
    assert "posterUrl" in joker
    assert "trailerUrl" in joker

