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
    
    def getLikedGenres(self,reviewList:Dict[str, Dict[str,Any]]) -> List[str]:
        """Get list of genres from user's reviewed movies"""
        genreCount = {}
        for movieName in reviewList:
            metadata = reviewList[movieName]["metadata"]
            if reviewList[movieName]["userRatingOutOf10"] < 6:
                continue  
            genres = metadata.movieGenres
            for genre in genres:
                if genre in genreCount:
                    genreCount[genre] += 1
                else:
                    genreCount[genre] = 1

        # Sort genres by count and return top genres
        sortedGenres = sorted(genreCount.items(), key=lambda x: x[1], reverse=True)
        topGenres = [genre for genre, count in sortedGenres[:5]] 
        return topGenres
    
        



    
