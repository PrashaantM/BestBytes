from backend.services.moviesService import listMovies, searchMovies
from pathlib import Path
from repositories.itemsRepo import loadMetadata
from routers.reviewRouter import movieReviews_memory
from typing import Dict, List, Any
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


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
    
    def getTop5Movies(self,reviewList:Dict[str, Dict[str,Any]]) -> List[str]:
        """Get top 5 movies reviewed by user based on rating"""
        ratedMovies = []
        for movieName in reviewList:
            rating = reviewList[movieName]["userRatingOutOf10"]
            ratedMovies.append((movieName, rating))
        
        # Sort by rating descending
        ratedMovies.sort(key=lambda x: x[1], reverse=True)
        top5 = [movie for movie, rating in ratedMovies[:5]]
        return top5
    
        
    def recommendMovies(self, username: str, numRecommendations: int = 5) -> List[Dict[str, Any]]:
        """Recommend movies based on user's review history"""
        userReviewHistory = self.getUserReviewHistory(username)
        likedGenres = self.getLikedGenres(userReviewHistory)
        top5Movies = self.getTop5Movies(userReviewHistory)
        if not userReviewHistory or not likedGenres or not top5Movies:
            return []  # No reviews, cannot recommend

    
        allOtherMovies = {}
        for movie in self.dataFolder.iterdir():
            if movie.is_dir() and movie.name not in userReviewHistory:
                try:
                    metadata = loadMetadata(movie)
                    allOtherMovies[movie.name] = metadata
                except Exception:
                    continue
        if not allOtherMovies:
            return []  # No other movies to recommend
            
        topRateDescriptions = []
        for movie in top5Movies:
            try:
                topRateDescriptions.append(userReviewHistory[movie]["metadata"])
            except Exception:
                continue
        
        descriptions = [allOtherMovies[movie].description for movie in allOtherMovies.keys()]
        vectored = TfidfVectorizer(max_features=200, stop_words='english')            

        try:

            tfidfMatrix = vectored.fit_transform(descriptions)
            topMovieVector = vectored.transform(topRateDescriptions)

            similarities = cosine_similarity(topMovieVector, tfidfMatrix).mean(axis=0)
        except Exception:
            similarities = np.zeros(len(allOtherMovies))

        recommended = []

        movies = list(allOtherMovies.keys())

        for idx, movieName in enumerate(movies):
            metadata = allOtherMovies[movieName]

            #score from 0-1 for matching genres
            genreMatch = sum(1 for genre in metadata.movieGenres if genre in likedGenres)/len(likedGenres) if likedGenres else 0

            #Score of 0-1 for a cosine similarity between movie descriptions
            contentMatch = float(similarities[idx]) if idx < len(similarities) else 0.0

            finalScore = (0.6 * genreMatch) + (0.4 * contentMatch)

            recommended.append({"title":movieName, "Match Score":finalScore, "Genre Score": genreMatch,"Content Score": contentMatch, "Metadata":metadata})

            recommended.sort(key=lambda x: x["Match Score"], reverse=True)
            return recommended[:numRecommendations]
            