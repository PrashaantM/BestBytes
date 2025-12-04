import pytest
from unittest.mock import Mock, patch
from backend.services.movieRecommendationService import MovieRecommendationService
from pathlib import Path
from backend.schemas.movieReviews import movieReviews
from backend.schemas.movie import movie


    
@pytest.fixture
def mockMovieReviews():
    return {
        "Inception": [
            movieReviews(
                user="alice",
                reviewText="Great movie!",
                review="Great movie!",
                reviewTitle="Loved it",
                dateOfReview="2023-01-01",
                userRatingOutOf10=9,
                usefulnessVote=5,
                totalVotes=10
            ),
            movieReviews(
                user="bob",
                reviewText="Not bad",
                review="Not bad",
                reviewTitle="Ok",
                dateOfReview="2023-01-02",
                userRatingOutOf10=7,
                usefulnessVote=3,
                totalVotes=5
            ),
        ],
        "The Shining": [
            movieReviews(
                user="alice",
                reviewText="Scary!",
                review="Scary!",
                reviewTitle="Terrifying",
                dateOfReview="2023-02-01",
                userRatingOutOf10=8,
                usefulnessVote=4,
                totalVotes=8
            ),
        ],
        "Interstellar": [
            movieReviews(
                user="charlie",
                reviewText="Mind-blowing",
                review="Mind-blowing",
                reviewTitle="Epic",
                dateOfReview="2023-03-01",
                userRatingOutOf10=10,
                usefulnessVote=6,
                totalVotes=12
            ),
        ],
    }
    
@pytest.fixture
def mockMetadataMap():
    return {
        "Inception": movie(
        title="Inception",
        movieIMDbRating=8.8,
        totalRatingCount=2000000,
        totalUserReviews="1.5M",
        totalCriticReviews="2k",
        metaScore="74",
        movieGenres=["Action", "Sci-Fi"],
        directors=["Christopher Nolan"],
        datePublished="2010-07-16",
        creators=["Christopher Nolan"],
        mainStars=["Leonardo DiCaprio"],
        description="A thief who steals corporate secrets through dream-sharing technology.",
        reviews=[],
        posterUrl=None,
        trailerUrl=None
    ),
    "The Shining": movie(
        title="The Shining",
        movieIMDbRating=8.4,
        totalRatingCount=600000,
        totalUserReviews="500k",
        totalCriticReviews="1k",
        metaScore="66",
        movieGenres=["Horror"],
        directors=["Stanley Kubrick"],
        datePublished="1980-05-23",
        creators=["Stephen King"],
        mainStars=["Jack Nicholson"],
        description="A family heads to an isolated hotel for the winter where a sinister presence influences the father.",
        reviews=[],
        posterUrl=None,
        trailerUrl=None
    ),
    "Interstellar": movie(
        title="Interstellar",
        movieIMDbRating=8.6,
        totalRatingCount=1200000,
        totalUserReviews="1M",
        totalCriticReviews="1.5k",
        metaScore="74",
        movieGenres=["Adventure", "Drama", "Sci-Fi"],
        directors=["Christopher Nolan"],
        datePublished="2014-11-07",
        creators=["Jonathan Nolan"],
        mainStars=["Matthew McConaughey"],
        description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        reviews=[],
        posterUrl=None,
        trailerUrl=None
   )}
    
@pytest.fixture
def service():
    """Instantiate the MovieRecommendationService with mocked data"""
    with patch('backend.services.movieRecommendationService.listMovies') as mockList:
        mockList.return_value = []
        service = MovieRecommendationService()
    return service

def mockPath(name, is_dir=True):
    mock_path = Mock(spec=Path)
    mock_path.name = name
    mock_path.is_dir.return_value = is_dir
    return mock_path
    


class TestGetUserReviewHistory:
   
    def testGetUserReviewHistory(self, service,mockMovieReviews, mockMetadataMap):
        paths = [
            mockPath("Inception"),
            mockPath("The Shining"),
            mockPath("Interstellar")
        ]
        with patch.object(service, "dataFolder") as mockDataFolder, \
             patch('backend.services.movieRecommendationService.movieReviews_memory', mockMovieReviews), \
             patch('backend.services.movieRecommendationService.loadMetadata', side_effect=lambda path:mockMetadataMap[path.name]):

            mockDataFolder.iterdir.return_value = paths

            resultingReview = service.getUserReviewHistory("alice")

            assert "Inception" in resultingReview
            assert "The Shining" in resultingReview
            assert "Interstellar" not in resultingReview

            assert resultingReview["Inception"]["review"] == "Great movie!"
            assert resultingReview["Inception"]["metadata"] ==  mockMetadataMap["Inception"]


        