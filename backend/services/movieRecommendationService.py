from backend.services.moviesService import listMovies, searchMovies
from pathlib import Path
from repositories.itemsRepo import loadMetadata
from routers.reviewRouter import movieReviews_memory
from typing import Dict, List, Any

class MovieRecommendationService:

    def __init__(self):
        self.dataFolder = Path("backend/data")
        self.movies = listMovies()


    def getUserReviewHistory(self, username: str) -> Dict[str, Dict[str,Any]]:
        """Get all reviews made by a specific user from in-memory storage"""
        userReviews : Dict[str, Dict[str,Any]] = {}
        for movie in self.dataFolder.iterdir():
            if movie.is_dir():
                reviews = movieReviews_memory.get(movie.name, [])
                for review in reviews:
                    if review.user == username:
                        userReviews[movie.name] = {
                            "review": review.review,
                            "userRatingOutOf10": review.userRatingOutOf10,
                            "usefulnessVote": review.usefulnessVote,
                            "totalVotes": review.totalVotes
                        }
                        userReviews[movie.name]["metadata"] = loadMetadata(movie)
        return userReviews
        



    
