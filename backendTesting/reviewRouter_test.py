import pytest
import json
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backend.routers.reviewRouter import router, movieReviews_memory
from backend.schemas.movieReviews import movieReviews
from backend.schemas.movie import movie

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def tmpPath(tmp_path):
    """Provide temporary directory for test files"""
    return tmp_path


# Test constants
DUMMY_REVIEW = {
    "dateOfReview": "2024-01-01",
    "user": "Khushi",
    "usefulnessVote": 5,
    "totalVotes": 7,
    "userRatingOutOf10": 9,
    "reviewTitle": "Amazing!",
    "review": "Great movie!"
}

MOCK_MOVIE_BASE = {
    "title": "Joker",
    "datePublished": "2019",
    "movieIMDbRating": 8.4,
    "totalRatingCount": 1000,
    "totalUserReviews": "500",
    "totalCriticReviews": "300",
    "metaScore": "59",
    "movieGenres": ["Crime", "Drama"],
    "movieRuntime": "122 min",
    "directors": ["Todd Phillips"],
    "creators": ["Todd Phillips", "Scott Silver"],
    "mainStars": ["Joaquin Phoenix", "Robert De Niro"],
    "description": "A gritty character study of Arthur Fleck, a man disregarded by society."
}


@pytest.fixture(autouse=True)
def clearMemory():
    """Reset in-memory reviews before each test."""
    movieReviews_memory.clear()
def createMockMovie(reviews=None, **overrides):
    """Helper to create mock movie objects with all required fields"""
    movieData = {**MOCK_MOVIE_BASE, **overrides}
    if reviews is not None:
        movieData["reviews"] = reviews
    else:
        movieData["reviews"] = []
    return movie(**movieData)


class TestGetAllReviewsForMovie:
    """Tests for GET /{title}/reviews"""

    def testGetReviewsSuccess(self, tmp_path, monkeypatch):
        """Successfully get reviews for a movie"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie:
            mockGetMovie.return_value = mockMovie
            
            response = client.get("/Joker/reviews")
            
            assert response.status_code == 200
            assert response.json()[0]["reviewTitle"] == "Amazing!"

    def testGetReviewsMovieNotFound(self):
        """404 when movie doesn't exist"""
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie:
            from fastapi import HTTPException
            mockGetMovie.side_effect = HTTPException(status_code=404, detail="Movie not found")
            
            response = client.get("/UnknownMovie/reviews")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def testGetReviewsNoneExist(self):
        """404 when movie has no reviews"""
        
        mockMovie = createMockMovie(reviews=[])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie:
            mockGetMovie.return_value = mockMovie
            
            response = client.get("/Joker/reviews")
            
            assert response.status_code == 404
            # The endpoint returns either "No reviews found" or "Movie not found"
            assert "not found" in response.json()["detail"].lower()


class TestGetReviewsByUser:
    """Tests for GET /user/{username}"""

    def testGetUserReviewsSuccess(self):
        """Successfully get all reviews by a user"""
        
        mockMovies = [
            createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        ]
        
        with patch("backend.services.moviesService.listMovies") as mockListMovies:
            mockListMovies.return_value = mockMovies
            
            response = client.get("/user/Khushi")
            
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["user"] == "Khushi"

    def testGetUserReviewsCaseInsensitive(self):
        """User search is case-insensitive"""
        
        mockMovies = [
            createMockMovie(reviews=[movieReviews(**{**DUMMY_REVIEW, "user": "khushi"})])
        ]
        
        with patch("backend.services.moviesService.listMovies") as mockListMovies:
            mockListMovies.return_value = mockMovies
            
            response = client.get("/user/KHUSHI")
            
            assert response.status_code == 200
            assert response.json()[0]["user"].lower() == "khushi"

    def testGetUserReviewsAcrossMultipleMovies(self):
        """Get reviews from multiple movies"""
        
        mockMovies = [
            createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)]),
            createMockMovie(
                title="Batman",
                datePublished="1989",
                movieIMDbRating=7.5,
                reviews=[movieReviews(**{**DUMMY_REVIEW, "reviewTitle": "Nice!"})]
            )
        ]
        
        with patch("backend.services.moviesService.listMovies") as mockListMovies:
            mockListMovies.return_value = mockMovies
            
            response = client.get("/user/Khushi")
            
            assert response.status_code == 200
            assert len(response.json()) == 2

    def testGetUserReviewsNotFound(self):
        """404 when user has no reviews"""
        
        mockMovies = [
            createMockMovie(reviews=[])
        ]
        
        with patch("backend.services.moviesService.listMovies") as mockListMovies:
            mockListMovies.return_value = mockMovies
            
            response = client.get("/user/UnknownUser")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "No reviews found for this user"

        response = client.get("/user/Khushi")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def testGetUserReviewsNotFound(self):
        response = client.get("/user/UnknownUser")
        assert response.status_code == 404
        assert response.json()["detail"] == "No reviews found for this user"

class TestUpdateReview:
    """Tests for PUT /{title}/review/{index}"""

    def testUpdateReviewSuccess(self):
        """User updates their own review successfully"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        
        updatedPayload = {
            "dateOfReview": "2024-01-02",
            "user": "SHOULD_NOT_CHANGE",
            "usefulnessVote": 9,
            "totalVotes": 10,
            "userRatingOutOf10": 8,
            "reviewTitle": "Updated!",
            "review": "Still good!"
        }
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.routers.reviewRouter.serviceUpdateReview") as mockUpdateReview, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockUpdateReview.return_value = movieReviews(**{**updatedPayload, "user": "Khushi"})
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.put("/Joker/review/0?sessionToken=abc", json=updatedPayload)
            
            assert response.status_code == 200
            body = response.json()
            assert body["reviewTitle"] == "Updated!"
            assert body["review"] == "Still good!"
            assert body["user"] == "Khushi"

    def testUpdateReviewUnauthenticated(self):
        """Missing/invalid token -> 401"""
        
        with patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            mockGetUser.return_value = None
            
            response = client.put("/Joker/review/0?sessionToken=BAD", json=DUMMY_REVIEW)
            
            assert response.status_code == 401
            assert "Login required" in response.json()["detail"]

    def testUpdateReviewNotFoundIndex(self):
        """Index exceeds list length -> 404"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.put("/Joker/review/10?sessionToken=abc", json=DUMMY_REVIEW)
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Review not found"

    def testUpdateReviewWrongUserForbidden(self):
        """User tries updating someone else's review -> 403"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**{**DUMMY_REVIEW, "user": "OtherUser"})])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.put("/Joker/review/0?sessionToken=abc", json=DUMMY_REVIEW)
            
            assert response.status_code == 403
            assert "update others" in response.json()["detail"].lower()


class TestDeleteReview:
    """Tests for DELETE /{title}/review/{index}"""

    def testDeleteReviewSuccess(self):
        """User deletes their own review -> success"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.routers.reviewRouter.serviceDeleteReview") as mockDeleteReview, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockDeleteReview.return_value = {"message": "Deleted review 'Amazing!' by Khushi"}
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.delete("/Joker/review/0?sessionToken=abc")
            
            assert response.status_code == 200
            assert "Deleted review" in response.json()["message"]

    def testDeleteReviewUnauthenticated(self):
        """User not logged in -> 401"""
        
        with patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            mockGetUser.return_value = None
            
            response = client.delete("/Joker/review/0?sessionToken=bad")
            
            assert response.status_code == 401
            assert response.json()["detail"] == "Login required to Delete Reviews"

    def testDeleteReviewMovieNotFound(self):
        """Movie folder missing -> 404"""
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            from fastapi import HTTPException
            mockGetMovie.side_effect = HTTPException(status_code=404, detail="Movie not found")
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.delete("/Joker/review/0?sessionToken=abc")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def testDeleteReviewIndexNotFound(self):
        """Index out of range -> 404"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**DUMMY_REVIEW)])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockGetUser.return_value = type("User", (), {"username": "Khushi"})()
            
            response = client.delete("/Joker/review/5?sessionToken=abc")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Review not found"

    def testDeleteReviewWrongUserForbidden(self):
        """User tries to delete someone else's review -> 403"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**{**DUMMY_REVIEW, "user": "Khushi"})])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockGetUser.return_value = type("User", (), {"username": "OtherUser"})()
            
            response = client.delete("/Joker/review/0?sessionToken=abc")
            
            assert response.status_code == 403
            assert response.json()["detail"] == "You can't delete others' reviews"

    def testDeleteReviewAdminOverride(self):
        """Admin can delete any user's review (success)"""
        
        mockMovie = createMockMovie(reviews=[movieReviews(**{**DUMMY_REVIEW, "user": "ADMIN"})])
        
        with patch("backend.routers.reviewRouter.getMovieByName") as mockGetMovie, \
             patch("backend.routers.reviewRouter.serviceDeleteReview") as mockDeleteReview, \
             patch("backend.users.user.User.getCurrentUser") as mockGetUser:
            
            mockGetMovie.return_value = mockMovie
            mockDeleteReview.return_value = {"message": "Deleted review 'Amazing!' by ADMIN"}
            mockGetUser.return_value = type("User", (), {"username": "AdminUser", "role": "admin"})()
            
            response = client.delete("/Joker/review/0?sessionToken=admin123")
            
            assert response.status_code == 200
            assert "Deleted review" in response.json()["message"]


class TestAddReview:
    """Tests for POST /{title} - Add a new review"""

    def testAddReviewSuccess(self, tmpPath):
        """Successfully add a review to an existing movie"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing movie!",
            "review": "This is a great film."
        }
        
        mockReview = movieReviews(**reviewPayload)
        
        with patch("backend.routers.reviewRouter.serviceAddReview") as mockAddReview, \
             patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            mockAddReview.return_value = mockReview
            
            response = client.post(
                "/The Dark Knight?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 200
        body = response.json()
        assert body["reviewTitle"] == "Amazing movie!"
        assert body["user"] == "testUser"

    def testAddReviewUnauthenticated(self, tmpPath):
        """401 when no valid session token"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing movie!",
            "review": "This is a great film."
        }
        
        with patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = None
            
            response = client.post(
                "/The Dark Knight?sessionToken=invalid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 401
        assert "Login required" in response.json()["detail"]

    def testAddReviewMovieNotFound(self, tmpPath):
        """404 when movie doesn't exist"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing movie!",
            "review": "This is a great film."
        }
        
        with patch("backend.routers.reviewRouter.serviceAddReview") as mockAddReview, \
             patch("backend.users.user.User.getCurrentUser") as mockUser, \
             patch("backend.routers.reviewRouter.getOrImportMovie") as mockGetMovie:
            
            from fastapi import HTTPException
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            mockGetMovie.side_effect = HTTPException(status_code=404, detail="Movie not found")
            mockAddReview.side_effect = HTTPException(status_code=404, detail="Movie not found")
            
            response = client.post(
                "/NonExistentMovie?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Review not found"


    def testDeleteReviewWrongUserForbidden(self, tmp_path, monkeypatch):
        """User tries to delete someone else’s review -> 403"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        movieReviews_memory["joker"] = [
            movieReviews(**{**DUMMY_REVIEW, "user": "Khushi"})
        ]

        # not user's review
        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "OtherUser"})
        )

        response = client.delete("/Joker/review/0?sessionToken=abc")
        assert response.status_code == 403
        assert response.json()["detail"] == "You can't delete others' reviews"

    def testDeleteReviewAdminOverride(self, tmp_path, monkeypatch):
        #Admin can delete any user's review (success)

        # movie folder
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        # data path
        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

    def testAddReviewInvalidDateFormat(self, tmpPath):
        """400 when date format is invalid"""
        
        reviewPayload = {
            "dateOfReview": "Nov 28th 2025",  # Invalid format
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing movie!",
            "review": "This is a great film."
        }
        
        with patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            
            response = client.post(
                "/The Dark Knight?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 400
        assert "YYYY-MM-DD" in response.json()["detail"]

    def testAddReviewEmptyReviewTitle(self, tmpPath):
        """400 when review title is empty"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "   ",  # Empty/whitespace only
            "review": "This is a great film."
        }
        
        with patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            
            response = client.post(
                "/The Dark Knight?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def testAddReviewEmptyReviewText(self, tmpPath):
        """400 when review text is empty"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 0,
            "totalVotes": 0,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing!",
            "review": "   "  # Empty/whitespace only
        }
        
        with patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            
            response = client.post(
                "/The Dark Knight?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def testAddReviewPersistsToCsv(self, tmpPath):
        """Verify review is actually saved via service call"""
        
        reviewPayload = {
            "dateOfReview": "2025-11-28",
            "user": "testUser",
            "usefulnessVote": 5,
            "totalVotes": 10,
            "userRatingOutOf10": 9.5,
            "reviewTitle": "Amazing movie!",
            "review": "This is a great film."
        }
        
        mockReview = movieReviews(**reviewPayload)
        
        with patch("backend.routers.reviewRouter.serviceAddReview") as mockAddReview, \
             patch("backend.users.user.User.getCurrentUser") as mockUser:
            
            mockUser.return_value = type("User", (), {"username": "testUser"})()
            mockAddReview.return_value = mockReview
            
            response = client.post(
                "/The Dark Knight?sessionToken=valid_token",
                json=reviewPayload
            )
        
        assert response.status_code == 200
        
        # Verify serviceAddReview was called with correct arguments
        mockAddReview.assert_called_once()
        call_args = mockAddReview.call_args
        assert call_args[0][0] == "The Dark Knight"
        assert call_args[0][1].reviewTitle == "Amazing movie!"
