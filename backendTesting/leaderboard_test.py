import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.routers.reviewRouter import router, movieReviews_memory
from backend.schemas.movieReviews import movieReviews

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_memory():
    """Reset the movieReviews_memory before each test."""
    movieReviews_memory.clear()
    yield
    movieReviews_memory.clear()


class TestLeaderboard:
    """Tests for GET /leaderboard endpoint"""

    def test_leaderboard_empty(self):
        """Empty leaderboard when no reviews exist"""
        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert response.json() == []

    def test_leaderboard_single_reviewer(self):
        """Leaderboard with one reviewer"""
        movieReviews_memory["joker"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="Alice",
                usefulnessVote=10,
                totalVotes=12,
                userRatingOutOf10=8.5,
                reviewTitle="Great movie",
                review="Loved it"
            )
        ]

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rank"] == 1
        assert data[0]["username"] == "alice"
        assert data[0]["totalReviews"] == 1
        assert data[0]["totalUsefulnessVotes"] == 10

    def test_leaderboard_multiple_reviewers(self):
        """Leaderboard with multiple reviewers, sorted by score"""
        movieReviews_memory["joker"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="Alice",
                usefulnessVote=100,
                totalVotes=120,
                userRatingOutOf10=8.0,
                reviewTitle="Review 1",
                review="Good"
            ),
            movieReviews(
                dateOfReview="2024-01-02",
                user="Bob",
                usefulnessVote=50,
                totalVotes=60,
                userRatingOutOf10=7.0,
                reviewTitle="Review 2",
                review="Nice"
            )
        ]
        
        movieReviews_memory["batman"] = [
            movieReviews(
                dateOfReview="2024-01-03",
                user="Alice",
                usefulnessVote=80,
                totalVotes=100,
                userRatingOutOf10=9.0,
                reviewTitle="Review 3",
                review="Amazing"
            )
        ]

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        # Alice should be #1 (2 reviews, 180 total usefulness votes)
        # Bob should be #2 (1 review, 50 total usefulness votes)
        assert len(data) == 2
        assert data[0]["username"] == "alice"
        assert data[0]["rank"] == 1
        assert data[0]["totalReviews"] == 2
        assert data[0]["totalUsefulnessVotes"] == 180
        
        assert data[1]["username"] == "bob"
        assert data[1]["rank"] == 2
        assert data[1]["totalReviews"] == 1

    def test_leaderboard_with_limit(self):
        """Test that leaderboard returns top 10 reviewers"""
        for i in range(15):
            movieReviews_memory[f"movie{i}"] = [
                movieReviews(
                    dateOfReview="2024-01-01",
                    user=f"User{i}",
                    usefulnessVote=10 * i,
                    totalVotes=20,
                    userRatingOutOf10=8.0,
                    reviewTitle="Review",
                    review="Good"
                )
            ]

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10  # Should return top 10
        
        # Check ranks are sequential
        for i, entry in enumerate(data, start=1):
            assert entry["rank"] == i

    def test_leaderboard_with_min_reviews(self):
        """Test that all reviewers with at least 1 review are included"""
        movieReviews_memory["movie1"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="PowerUser",
                usefulnessVote=50,
                totalVotes=60,
                userRatingOutOf10=8.0,
                reviewTitle="Review 1",
                review="Good"
            ),
            movieReviews(
                dateOfReview="2024-01-02",
                user="PowerUser",
                usefulnessVote=40,
                totalVotes=50,
                userRatingOutOf10=7.5,
                reviewTitle="Review 2",
                review="Nice"
            ),
            movieReviews(
                dateOfReview="2024-01-03",
                user="CasualUser",
                usefulnessVote=30,
                totalVotes=40,
                userRatingOutOf10=6.0,
                reviewTitle="One review",
                review="OK"
            )
        ]

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        # Both users should appear (PowerUser with 2 reviews ranked higher)
        assert len(data) == 2
        assert data[0]["username"] == "poweruser"  # Ranked first
        assert data[0]["totalReviews"] == 2
        assert data[1]["username"] == "casualuser"  # Ranked second
        assert data[1]["totalReviews"] == 1

    def test_leaderboard_helpfulness_score_calculation(self):
        """Test that helpfulness score is calculated correctly"""
        movieReviews_memory["movie1"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="TestUser",
                usefulnessVote=80,
                totalVotes=100,
                userRatingOutOf10=8.0,
                reviewTitle="Test",
                review="Test"
            )
        ]

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        # Score = (80 * 0.8) + (1 * 10) = 64 + 10 = 74
        assert len(data) == 1
        assert data[0]["helpfulnessScore"] == 74.0
        assert data[0]["averageUsefulnessRatio"] == 0.8


class TestReviewerStats:
    """Tests for GET /stats/{username} endpoint"""

    def test_stats_user_not_found(self):
        """404 when user has no reviews"""
        response = client.get("/stats/nonexistent")
        assert response.status_code == 404
        assert "No reviews found" in response.json()["detail"]

    def test_stats_single_review(self):
        """Stats for user with one review"""
        movieReviews_memory["joker"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="Alice",
                usefulnessVote=10,
                totalVotes=12,
                userRatingOutOf10=8.5,
                reviewTitle="Great",
                review="Loved it"
            )
        ]

        response = client.get("/stats/Alice")
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "alice"
        assert data["totalReviews"] == 1
        assert data["totalUsefulnessVotes"] == 10
        assert data["averageRating"] == 8.5
        # 10/12 = 0.8333...
        assert abs(data["averageUsefulnessRatio"] - 0.8333) < 0.0001

    def test_stats_multiple_reviews(self):
        """Stats aggregated across multiple reviews"""
        movieReviews_memory["joker"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="Bob",
                usefulnessVote=50,
                totalVotes=100,
                userRatingOutOf10=8.0,
                reviewTitle="Review 1",
                review="Good"
            )
        ]
        
        movieReviews_memory["batman"] = [
            movieReviews(
                dateOfReview="2024-01-02",
                user="Bob",
                usefulnessVote=30,
                totalVotes=50,
                userRatingOutOf10=6.0,
                reviewTitle="Review 2",
                review="OK"
            )
        ]

        response = client.get("/stats/bob")
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "bob"
        assert data["totalReviews"] == 2
        assert data["totalUsefulnessVotes"] == 80  # 50 + 30
        assert data["averageRating"] == 7.0  # (8.0 + 6.0) / 2
        # (50 + 30) / (100 + 50) = 80/150 = 0.5333...
        assert abs(data["averageUsefulnessRatio"] - 0.5333) < 0.0001

    def test_stats_case_insensitive(self):
        """Stats lookup is case-insensitive"""
        movieReviews_memory["movie"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="TestUser",
                usefulnessVote=10,
                totalVotes=20,
                userRatingOutOf10=7.0,
                reviewTitle="Test",
                review="Test"
            )
        ]

        response1 = client.get("/stats/TestUser")
        response2 = client.get("/stats/testuser")
        response3 = client.get("/stats/TESTUSER")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        assert response1.json() == response2.json() == response3.json()

    def test_stats_zero_total_votes(self):
        """Handle edge case of zero total votes"""
        movieReviews_memory["movie"] = [
            movieReviews(
                dateOfReview="2024-01-01",
                user="NewUser",
                usefulnessVote=0,
                totalVotes=0,
                userRatingOutOf10=5.0,
                reviewTitle="Test",
                review="Test"
            )
        ]

        response = client.get("/stats/NewUser")
        assert response.status_code == 200
        data = response.json()
        
        # Should handle division by zero gracefully
        assert data["averageUsefulnessRatio"] == 0.0
