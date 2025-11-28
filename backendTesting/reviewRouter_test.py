import pytest
import json
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.routers.reviewRouter import router, movieReviews_memory
from backend.schemas.movieReviews import movieReviews

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# test review case
DUMMY_REVIEW = {
    "dateOfReview": "2024-01-01",
    "user": "Khushi",
    "usefulnessVote": 5,
    "totalVotes": 7,
    "userRatingOutOf10": 9,
    "reviewTitle": "Amazing!",
    "review": "Great movie!"
}


@pytest.fixture(autouse=True)
def clearMemory():
    """Reset in-memory reviews before each test."""
    movieReviews_memory.clear()


class TestGetAllReviewsForMovie:
    """Tests for GET /{title}/reviews"""

    def testGetReviewsSuccess(self, tmp_path, monkeypatch):
        
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        
        movieReviews_memory["joker"] = [
            movieReviews(**DUMMY_REVIEW)
        ]

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        response = client.get("/Joker/reviews")
        assert response.status_code == 200
        assert response.json()[0]["reviewTitle"] == "Amazing!"

    def testGetReviewsMovieNotFound(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        response = client.get("/UnknownMovie/reviews")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def testGetReviewsNoneExist(self, tmp_path, monkeypatch):
        
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        response = client.get("/Joker/reviews")
        assert response.status_code == 404
        assert response.json()["detail"] == "No reviews found for this movie"


class TestGetReviewsByUser:
    """Tests for GET /user/{username}"""

    def testGetUserReviewsSuccess(self):
        movieReviews_memory["joker"] = [
            movieReviews(**DUMMY_REVIEW)
        ]

        response = client.get("/user/Khushi")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["user"] == "Khushi"

    def testGetUserReviewsCaseInsensitive(self):
        movieReviews_memory["joker"] = [
            movieReviews(**{**DUMMY_REVIEW, "user": "khushi"})
        ]

        response = client.get("/user/KHUSHI")
        assert response.status_code == 200
        assert response.json()[0]["user"].lower() == "khushi"

    def testGetUserReviewsAcrossMultipleMovies(self):
        movieReviews_memory["joker"] = [
            movieReviews(**DUMMY_REVIEW)
        ]
        movieReviews_memory["batman"] = [
            movieReviews(**{**DUMMY_REVIEW, "reviewTitle": "Nice!"})
        ]

        response = client.get("/user/Khushi")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def testGetUserReviewsNotFound(self):
        response = client.get("/user/UnknownUser")
        assert response.status_code == 404
        assert response.json()["detail"] == "No reviews found for this user"

class TestUpdateReview:
    """Tests for PUT /{title}/review/{index}"""

    def testUpdateReviewSuccess(self, tmp_path, monkeypatch):
        """User updates their own review successfully"""

        # create movie folder
        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        movieReviews_memory["joker"] = [
            movieReviews(**DUMMY_REVIEW)
        ]

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        updated_payload = {
            "dateOfReview": "2024-01-02",
            "user": "SHOULD_NOT_CHANGE",
            "usefulnessVote": 9,
            "totalVotes": 10,
            "userRatingOutOf10": 8,
            "reviewTitle": "Updated!",
            "review": "Still good!"
        }

        # mock login
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("backend.users.user.User.getCurrentUser",
                       lambda *args, **kw: type("U", (), {"username": "Khushi"}))

            response = client.put("/Joker/review/0?sessionToken=abc", json=updated_payload)

        assert response.status_code == 200
        body = response.json()

        assert body["reviewTitle"] == "Updated!"
        assert body["review"] == "Still good!"
        assert body["user"] == "Khushi"          # MUST stay original user

    def testUpdateReviewUnauthenticated(self, tmp_path, monkeypatch):
        """Missing/invalid token -> 401"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]
        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("backend.users.user.User.getCurrentUser", lambda *a, **k: None)

            response = client.put("/Joker/review/0?sessionToken=BAD", json=DUMMY_REVIEW)

        assert response.status_code == 401
        assert "Login required" in response.json()["detail"]

    def testUpdateReviewNotFoundIndex(self, tmp_path, monkeypatch):
        """Index exceeds list length -> 404"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]
        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("backend.users.user.User.getCurrentUser",
                       lambda *a, **k: type("U", (), {"username": "Khushi"}))

            response = client.put("/Joker/review/10?sessionToken=abc", json=DUMMY_REVIEW)

        assert response.status_code == 404
        assert response.json()["detail"] == "Review not found"

    def testUpdateReviewWrongUserForbidden(self, tmp_path, monkeypatch):
        """User tries updating someone else's review -> 403"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        movieReviews_memory["joker"] = [
            movieReviews(**{**DUMMY_REVIEW, "user": "OtherUser"})
        ]

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("backend.users.user.User.getCurrentUser",
                       lambda *a, **k: type("U", (), {"username": "Khushi"}))

            response = client.put("/Joker/review/0?sessionToken=abc", json=DUMMY_REVIEW)

        assert response.status_code == 403
        assert "update others" in response.json()["detail"].lower()

    def testUpdateReviewMovieNotFound(self, tmp_path, monkeypatch):
        """Movie folder does not exist -> 404"""

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("backend.users.user.User.getCurrentUser",
                       lambda *a, **k: type("U", (), {"username": "Khushi"}))

            response = client.put("/Joker/review/0?sessionToken=abc", json=DUMMY_REVIEW)

        assert response.status_code == 404
        assert "Movie 'Joker' not found" in response.json()["detail"]

class TestDeleteReview:
    """Tests for DELETE /{title}/review/{index}"""

    def testDeleteReviewSuccess(self, tmp_path, monkeypatch):
        """User deletes their own review -> success"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        # one review by khushi
        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]

        # user khushi
        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "Khushi"})
        )

        response = client.delete("/Joker/review/0?sessionToken=abc")

        assert response.status_code == 200
        assert "Deleted review" in response.json()["message"]
        assert movieReviews_memory["joker"] == []


    def testDeleteReviewUnauthenticated(self, tmp_path, monkeypatch):
        """User not logged in -> 401"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]

        # no user test
        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser", lambda *a, **k: None
        )

        response = client.delete("/Joker/review/0?sessionToken=bad")
        assert response.status_code == 401
        assert response.json()["detail"] == "Login required to Delete Reviews"


    def testDeleteReviewMovieNotFound(self, tmp_path, monkeypatch):
        """Movie folder missing -> 404"""

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]

        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "Khushi"})
        )

        response = client.delete("/Joker/review/0?sessionToken=abc")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


    def testDeleteReviewIndexNotFound(self, tmp_path, monkeypatch):
        """Index out of range -> 404"""

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        movieReviews_memory["joker"] = [movieReviews(**DUMMY_REVIEW)]

        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "Khushi"})
        )

        response = client.delete("/Joker/review/5?sessionToken=abc")
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

        # one review by ADMIN
        movieReviews_memory["joker"] = [
            movieReviews(**{**DUMMY_REVIEW, "user": "ADMIN"})
        ]

        # mock admin user
        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "AdminUser", "role": "admin"})
        )

        response = client.delete("/Joker/review/0?sessionToken=admin123")

        assert response.status_code == 200
        assert "Deleted review" in response.json()["message"]
        assert movieReviews_memory["joker"] == []


    def testDeleteReviewUserNotAdminForbidden(self, tmp_path, monkeypatch):
        #Normal user tries to delete another user's review -> 403

        movie_dir = tmp_path / "Joker"
        movie_dir.mkdir()
        (movie_dir / "metadata.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr("backend.routers.reviewRouter.DATA_PATH", str(tmp_path))

        # review belongs to USER
        movieReviews_memory["joker"] = [
            movieReviews(**{**DUMMY_REVIEW, "user": "USER"})
        ]

        # current_user is NOT admin and not the review owner
        monkeypatch.setattr(
            "backend.users.user.User.getCurrentUser",
            lambda *a, **k: type("U", (), {"username": "RandomUser", "role": "user"})
        )

        response = client.delete("/Joker/review/0?sessionToken=user123")

        assert response.status_code == 403
        assert response.json()["detail"] == "You can't delete others' reviews"



