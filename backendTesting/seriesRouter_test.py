import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.routers.seriesRouter import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Mock an authenticated admin user."""
    user = MagicMock()
    user.username = "admin"
    user.isAdmin = True
    with patch("backend.users.user.User.getCurrentUser", return_value=user):
        yield user


@pytest.fixture
def mock_normal_user():
    """Mock a logged-in but NOT admin user."""
    user = MagicMock()
    user.username = "regular_user"
    user.isAdmin = False
    with patch("backend.users.user.User.getCurrentUser", return_value=user):
        yield user


@pytest.fixture
def mock_invalid_session():
    """Mock an invalid session token."""
    with patch("backend.users.user.User.getCurrentUser", return_value=None):
        yield


class TestGetAllSeries:
    # test to get all movie series

    def test_get_all_series_success(self):
        mock_data = {
            "Marvel": [{"title": "Iron Man", "order": 1}],
            "Batman": [{"title": "The Dark Knight", "order": 2}]
        }

        with patch("backend.routers.seriesRouter.listAllSeries", return_value=mock_data):
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == mock_data


class TestGetSeriesMovies:
    # test to get series by its name

    def test_get_series_movies_success(self):
        expected = [
            {"title": "Iron Man", "order": 1},
            {"title": "Iron Man 2", "order": 2},
        ]

        with patch("backend.routers.seriesRouter.getMoviesInSeries", return_value=expected):
            response = client.get("/Marvel")
            assert response.status_code == 200
            assert response.json() == expected

    def test_get_series_movies_not_found(self):
        with patch("backend.routers.seriesRouter.getMoviesInSeries", return_value=[]):
            response = client.get("/UnknownSeries")
            assert response.status_code == 404
            assert "No movies found" in response.json()["detail"]


class TestCreateSeries:
    # test to create series

    def test_create_series_success(self, mock_admin_user):
        movies = [("Iron Man", 1), ("Iron Man 2", 2)]

        with patch("backend.routers.seriesRouter.validateSeriesOrders") as mock_validate, \
             patch("backend.routers.seriesRouter.createSeries") as mock_create:

            response = client.post(
                "/create",
                params={
                    "seriesName": "Marvel",
                    "sessionToken": "valid",
                },
                json=movies
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Series 'Marvel' created successfully"
            mock_validate.assert_called_once()
            mock_create.assert_called_once_with("Marvel", movies)

    def test_create_series_unauthenticated(self, mock_invalid_session):
        movies = [("Iron Man", 1)]
        response = client.post(
            "/create",
            params={"seriesName": "Marvel", "sessionToken": "bad"},
            json=movies
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_create_series_forbidden_for_non_admin(self, mock_normal_user):
        movies = [("Iron Man", 1)]
        response = client.post(
            "/create",
            params={"seriesName": "Marvel", "sessionToken": "regular"},
            json=movies
        )
        assert response.status_code == 403
        assert "Admin privileges" in response.json()["detail"]

    def test_create_series_invalid_orders(self, mock_admin_user):
        movies = [("Iron Man", 1), ("Iron Man 2", 1)]  # duplicate order

        with patch("backend.routers.seriesRouter.validateSeriesOrders") as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Duplicate order values")

            response = client.post(
                "/create",
                params={"seriesName": "Marvel", "sessionToken": "valid"},
                json=movies
            )

            assert response.status_code == 400
            assert "Duplicate" in response.json()["detail"]


class TestUpdateSeries:
    # test to put movies in series

    def test_update_series_success(self, mock_admin_user):
        movies = [("Iron Man", 1), ("Iron Man 3", 2)]

        with patch("backend.routers.seriesRouter.validateSeriesOrders") as mock_validate, \
             patch("backend.routers.seriesRouter.updateSeries") as mock_update:

            response = client.put(
                "/update/Marvel",
                params={"sessionToken": "valid"},
                json=movies
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Series 'Marvel' updated successfully"
            mock_validate.assert_called_once()
            mock_update.assert_called_once_with("Marvel", movies)

    def test_update_series_not_admin(self, mock_normal_user):
        movies = [("Iron Man", 1)]
        response = client.put(
            "/update/Marvel",
            params={"sessionToken": "regular"},
            json=movies
        )
        assert response.status_code == 403
        assert "Admin privileges" in response.json()["detail"]

    def test_update_series_invalid_orders(self, mock_admin_user):
        movies = [("Iron Man", 1), ("Iron Man 3", 1)]

        with patch("backend.routers.seriesRouter.validateSeriesOrders") as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid series order")

            response = client.put(
                "/update/Marvel",
                params={"sessionToken": "valid"},
                json=movies
            )
            assert response.status_code == 400


class TestDeleteSeries:
    # delete test

    def test_delete_series_success(self, mock_admin_user):
        with patch("backend.routers.seriesRouter.deleteSeries", return_value={"message": "Deleted"}) as mock_delete:

            response = client.delete(
                "/Marvel",
                params={"sessionToken": "valid"}
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Deleted"
            mock_delete.assert_called_once_with("Marvel")

    def test_delete_series_forbidden(self, mock_normal_user):
        response = client.delete(
            "/Marvel",
            params={"sessionToken": "regular"}
        )
        assert response.status_code == 403

    def test_delete_series_unauthenticated(self, mock_invalid_session):
        response = client.delete(
            "/Marvel",
            params={"sessionToken": "invalid"}
        )
        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]


class TestSeriesProgress:
    """Tests for GET /{seriesName}/progress/{username}"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset watched list and patch movie retrieval"""
        from backend.routers.listsRouter import userMovieLists
        userMovieLists.clear()
        userMovieLists["khushi"] = {"watched": ["Iron Man"]}

    def test_series_progress_success(self, mock_admin_user):
        movies = [
            MagicMock(title="Iron Man"),
            MagicMock(title="Iron Man 2")
        ]

        with patch("backend.routers.seriesRouter.getMoviesInSeries", return_value=movies):
            response = client.get(
                "/Marvel/progress/khushi",
                params={"sessionToken": "valid"}
            )

        assert response.status_code == 200
        body = response.json()
        assert body["watched"] == 1
        assert body["totalMovies"] == 2
        assert body["progressPercent"] == 50.0

    def test_series_progress_series_not_found(self, mock_admin_user):
        with patch("backend.routers.seriesRouter.getMoviesInSeries", return_value=[]):
            response = client.get(
                "/Unknown/progress/khushi",
                params={"sessionToken": "valid"}
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_series_progress_user_not_found(self, mock_admin_user):
        from backend.routers.listsRouter import userMovieLists
        userMovieLists.clear()

        movies = [MagicMock(title="Iron Man")]

        with patch("backend.routers.seriesRouter.getMoviesInSeries", return_value=movies):
            response = client.get(
                "/Marvel/progress/khushi",
                params={"sessionToken": "valid"}
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "User has no lists"

    def test_series_progress_unauthenticated(self, mock_invalid_session):
        response = client.get(
            "/Marvel/progress/khushi",
            params={"sessionToken": "bad"}
        )
        assert response.status_code == 401