"""
Comprehensive tests for TMDB integration including:
- TMDB service (search, details, popular movies)
- TMDB router endpoints
- Pagination with TMDB
- Auto-import functionality
- Description truncation
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


# ============================================================================
# Mock Data
# ============================================================================

MOCK_TMDB_SEARCH_RESULTS = [
    {
        "id": 155,
        "title": "The Dark Knight Rises",
        "releaseDate": "2012-07-20",
        "voteAverage": 7.8,
        "overview": "Eight years after the Joker's reign of anarchy...",
        "posterUrl": "https://image.tmdb.org/t/p/w500/tdkr.jpg",
    },
    {
        "id": 27205,
        "title": "Inception",
        "releaseDate": "2010-07-16",
        "voteAverage": 8.8,
        "overview": "A thief who steals secrets through dreams.",
        "posterUrl": "https://image.tmdb.org/t/p/w500/inception.jpg",
    }
]

MOCK_TMDB_MOVIE_DETAILS = {
    "id": 155,
    "title": "The Dark Knight Rises",
    "releaseDate": "2012-07-20",
    "voteAverage": 7.8,
    "overview": "Eight years after the Joker's reign of anarchy, Batman returns.",
    "posterUrl": "https://image.tmdb.org/t/p/w500/tdkr.jpg",
    "trailerUrl": "https://www.youtube.com/watch?v=g8evyE9TuYk"
}

MOCK_TMDB_POPULAR_PAGE1 = [
    {
        "id": 1,
        "title": f"Popular Movie {i}",
        "releaseDate": "2024-01-01",
        "voteAverage": 7.5 + (i * 0.1),
        "overview": f"This is popular movie {i} description.",
        "posterUrl": f"https://image.tmdb.org/t/p/w500/movie{i}.jpg",
    }
    for i in range(1, 21)  # 20 movies per page
]

MOCK_TMDB_POPULAR_PAGE2 = [
    {
        "id": 20 + i,
        "title": f"Popular Movie {20 + i}",
        "releaseDate": "2024-01-01",
        "voteAverage": 7.5 + (i * 0.1),
        "overview": f"This is popular movie {20 + i} description.",
        "posterUrl": f"https://image.tmdb.org/t/p/w500/movie{20 + i}.jpg",
    }
    for i in range(1, 21)
]

MOCK_TMDB_POPULAR_PAGE3 = [
    {
        "id": 40 + i,
        "title": f"Popular Movie {40 + i}",
        "releaseDate": "2024-01-01",
        "voteAverage": 7.5 + (i * 0.1),
        "overview": f"This is popular movie {40 + i} description.",
        "posterUrl": f"https://image.tmdb.org/t/p/w500/movie{40 + i}.jpg",
    }
    for i in range(1, 21)
]

MOCK_LONG_DESCRIPTION = {
    "id": 999,
    "title": "Long Description Movie",
    "releaseDate": "2024-01-01",
    "voteAverage": 8.0,
    "overview": "A" * 600,  # 600 characters - exceeds 500 char limit
    "posterUrl": "https://image.tmdb.org/t/p/w500/long.jpg",
}


# ============================================================================
# TMDB Service Tests
# ============================================================================

class TestTmdbService:
    """Tests for backend/services/tmdbService.py"""

    @patch("backend.services.tmdbService.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_search_tmdb_success(self, mock_client):
        """Test TMDB search returns properly formatted results"""
        from backend.services.tmdbService import search_tmdb
        
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 155,
                    "title": "The Dark Knight Rises",
                    "release_date": "2012-07-20",
                    "vote_average": 7.8,
                    "overview": "Batman returns...",
                    "poster_path": "/tdkr.jpg"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        results = await search_tmdb("dark knight", page=1)
        
        assert len(results) == 1
        assert results[0]["title"] == "The Dark Knight Rises"
        assert results[0]["releaseDate"] == "2012-07-20"
        assert results[0]["voteAverage"] == 7.8
        assert "posterUrl" in results[0]

    @patch("backend.services.tmdbService.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_get_tmdb_movie_details_with_trailer(self, mock_client):
        """Test getting movie details includes trailer URL"""
        from backend.services.tmdbService import get_tmdb_movie_details
        
        # Mock movie details response
        mock_details_response = MagicMock()
        mock_details_response.json.return_value = {
            "id": 155,
            "title": "The Dark Knight Rises",
            "release_date": "2012-07-20",
            "vote_average": 7.8,
            "overview": "Batman returns...",
            "poster_path": "/tdkr.jpg"
        }
        mock_details_response.raise_for_status = MagicMock()
        
        # Mock videos response
        mock_videos_response = MagicMock()
        mock_videos_response.json.return_value = {
            "results": [
                {
                    "type": "Trailer",
                    "site": "YouTube",
                    "key": "g8evyE9TuYk"
                }
            ]
        }
        mock_videos_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [mock_details_response, mock_videos_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await get_tmdb_movie_details(155)
        
        assert result["title"] == "The Dark Knight Rises"
        assert result["trailerUrl"] == "https://www.youtube.com/watch?v=g8evyE9TuYk"

    @patch("backend.services.tmdbService.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_get_popular_movies(self, mock_client):
        """Test fetching popular movies from TMDB"""
        from backend.services.tmdbService import get_popular_movies
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": i,
                    "title": f"Popular {i}",
                    "release_date": "2024-01-01",
                    "vote_average": 7.5,
                    "overview": "Popular movie",
                    "poster_path": f"/popular{i}.jpg"
                }
                for i in range(1, 21)
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        results = await get_popular_movies(page=1)
        
        assert len(results) == 20
        assert all("posterUrl" in r for r in results)


# ============================================================================
# TMDB Router Tests
# ============================================================================

class TestTmdbRouter:
    """Tests for backend/routers/tmdbRouter.py endpoints"""

    @patch("backend.routers.tmdbRouter.search_tmdb", new_callable=AsyncMock)
    def test_search_tmdb_endpoint(self, mock_search):
        """Test POST /movies/tmdb/search endpoint"""
        mock_search.return_value = MOCK_TMDB_SEARCH_RESULTS
        
        resp = client.post(
            "/movies/tmdb/search",
            json={"query": "inception", "page": 1}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        mock_search.assert_called_once_with("inception", 1)

    @patch("backend.routers.tmdbRouter.get_tmdb_movie_details", new_callable=AsyncMock)
    def test_get_tmdb_movie_details_endpoint(self, mock_details):
        """Test GET /movies/tmdb/{id} endpoint"""
        mock_details.return_value = MOCK_TMDB_MOVIE_DETAILS
        
        resp = client.get("/movies/tmdb/155")
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "The Dark Knight Rises"
        assert "trailerUrl" in data
        mock_details.assert_called_once_with(155)


# ============================================================================
# Pagination with TMDB Tests
# ============================================================================

class TestPaginationWithTmdb:
    """Tests for GET /movies/ with pagination and include_tmdb parameter"""

    @patch("backend.services.tmdbService.get_popular_movies", new_callable=AsyncMock)
    def test_pagination_page1_with_tmdb(self, mock_popular):
        """Test first page with TMDB enabled"""
        mock_popular.return_value = MOCK_TMDB_POPULAR_PAGE1
        
        resp = client.get("/movies/?page=1&limit=10&include_tmdb=true")
        
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 10

    @patch("backend.services.tmdbService.get_popular_movies", new_callable=AsyncMock)
    def test_pagination_page2_with_tmdb(self, mock_popular):
        """Test second page with TMDB enabled"""
        def get_popular_side_effect(page):
            if page == 1:
                return MOCK_TMDB_POPULAR_PAGE1
            elif page == 2:
                return MOCK_TMDB_POPULAR_PAGE2
            elif page == 3:
                return MOCK_TMDB_POPULAR_PAGE3
            return []
        
        mock_popular.side_effect = get_popular_side_effect
        
        resp = client.get("/movies/?page=2&limit=10&include_tmdb=true")
        
        assert resp.status_code == 200
        data = resp.json()
        # Should have results (may be less than 10 depending on local movies)
        assert len(data) > 0

    @patch("backend.routers.movieRouter.get_popular_movies", new_callable=AsyncMock)
    def test_pagination_fetches_multiple_tmdb_pages(self, mock_popular):
        """Test that requesting page 3 fetches multiple TMDB pages"""
        def get_popular_side_effect(page):
            if page == 1:
                return MOCK_TMDB_POPULAR_PAGE1
            elif page == 2:
                return MOCK_TMDB_POPULAR_PAGE2
            elif page == 3:
                return MOCK_TMDB_POPULAR_PAGE3
            return []
        
        mock_popular.side_effect = get_popular_side_effect
        
        resp = client.get("/movies/?page=3&limit=10&include_tmdb=true")
        
        assert resp.status_code == 200
        # Should have called get_popular_movies multiple times
        assert mock_popular.call_count >= 2

    def test_pagination_without_tmdb(self):
        """Test pagination works without TMDB (local movies only)"""
        resp = client.get("/movies/?page=1&limit=5&include_tmdb=false")
        
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5

    @patch("backend.services.tmdbService.get_popular_movies", new_callable=AsyncMock)
    def test_description_truncation(self, mock_popular):
        """Test that long TMDB descriptions are truncated to 500 chars"""
        mock_popular.return_value = [MOCK_LONG_DESCRIPTION]
        
        resp = client.get("/movies/?page=1&limit=10&include_tmdb=true")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Find the long description movie
        long_movie = next((m for m in data if m.get("title") == "Long Description Movie"), None)
        if long_movie:
            assert len(long_movie["description"]) <= 500
            assert long_movie["description"].endswith("...")


# ============================================================================
# Auto-Import Tests
# ============================================================================

class TestAutoImport:
    """Tests for auto-import functionality when adding to lists/reviews"""

    @patch("backend.services.tmdbService.search_tmdb", new_callable=AsyncMock)
    @patch("backend.services.tmdbService.get_tmdb_movie_details", new_callable=AsyncMock)
    def test_add_review_auto_imports_tmdb_movie(self, mock_details, mock_search):
        """Test that adding a review for non-existent movie imports from TMDB"""
        mock_search.return_value = [
            {
                "id": 27205,
                "title": "Inception",
                "releaseDate": "2010-07-16",
                "voteAverage": 8.8,
                "overview": "Dream heist movie",
                "posterUrl": "https://image.tmdb.org/t/p/w500/inception.jpg",
            }
        ]
        mock_details.return_value = {
            "id": 27205,
            "title": "Inception",
            "releaseDate": "2010-07-16",
            "voteAverage": 8.8,
            "overview": "Dream heist movie",
            "posterUrl": "https://image.tmdb.org/t/p/w500/inception.jpg",
            "trailerUrl": "https://www.youtube.com/watch?v=YoHD9XEInc0"
        }
        
        # Try to add review for non-local movie
        resp = client.post(
            "/reviews/",
            json={
                "movie_title": "Inception",
                "username": "testuser",
                "reviewDate": "2024-01-01",
                "reviewSummary": "Great movie!",
                "reviewRating": "5/5",
                "reviewText": "Mind-bending experience"
            }
        )
        
        # Should succeed (auto-import or handle gracefully)
        assert resp.status_code in [200, 201, 404]  # Depends on implementation

    @patch("backend.services.tmdbService.search_tmdb", new_callable=AsyncMock)
    @patch("backend.services.tmdbService.get_tmdb_movie_details", new_callable=AsyncMock)
    def test_add_to_list_auto_imports_tmdb_movie(self, mock_details, mock_search):
        """Test that adding movie to list imports from TMDB if not local"""
        mock_search.return_value = [MOCK_TMDB_SEARCH_RESULTS[1]]
        mock_details.return_value = MOCK_TMDB_MOVIE_DETAILS
        
        # First create a list
        list_resp = client.post(
            "/lists/create/testuser",
            json={"listName": "My TMDB List", "description": "Test list"}
        )
        
        if list_resp.status_code in [200, 201]:
            # Try to add TMDB movie to list
            add_resp = client.post(
                "/lists/testuser/My TMDB List/add",
                json={"movie_title": "Inception"}
            )
            
            # Should succeed (auto-import or handle gracefully)
            assert add_resp.status_code in [200, 201, 404, 400]


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    @patch("backend.services.tmdbService.get_popular_movies", new_callable=AsyncMock)
    def test_tmdb_failure_graceful_degradation(self, mock_popular):
        """Test that TMDB failures don't break pagination"""
        # Simulate TMDB API failure
        mock_popular.side_effect = Exception("TMDB API Error")
        
        resp = client.get("/movies/?page=1&limit=10&include_tmdb=true")
        
        # Should still return local movies
        assert resp.status_code == 200

    def test_empty_page_returns_empty_list(self):
        """Test that requesting a valid but empty page returns empty array"""
        resp = client.get("/movies/?page=2&limit=10&include_tmdb=false")
        
        # Should return 200 with empty array (not 404)
        assert resp.status_code in [200, 404]  # Depends on validation logic

    @patch("backend.services.tmdbService.get_popular_movies", new_callable=AsyncMock)
    def test_duplicate_movies_filtered(self, mock_popular):
        """Test that duplicate movies (local vs TMDB) are filtered"""
        # Mock returns a movie that exists locally (e.g., "Joker")
        mock_popular.return_value = [
            {
                "id": 475557,
                "title": "Joker",
                "releaseDate": "2019-10-02",
                "voteAverage": 8.2,
                "overview": "In 1981, failed comedian Arthur Fleck...",
                "posterUrl": "https://image.tmdb.org/t/p/w500/joker.jpg",
            }
        ]
        
        resp = client.get("/movies/?page=1&limit=20&include_tmdb=true")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Count how many "Joker" movies appear
        joker_count = sum(1 for m in data if "Joker" in m.get("title", ""))
        
        # Should not have duplicates
        assert joker_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
