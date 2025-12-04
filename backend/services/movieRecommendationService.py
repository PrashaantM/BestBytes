from backend.services.moviesService import listMovies, searchMovies
from backend.routers.movieRouter import enrich_movies_with_tmdb_posters_via_search
from pathlib import Path
from backend.repositories.itemsRepo import loadMetadata
from backend.routers.reviewRouter import movieReviews_memory
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
        print(f"DEBUG: Getting review history for user: {username}")
        print(f"DEBUG: movieReviews_memory keys: {list(movieReviews_memory.keys())}")
        
        for movie in self.dataFolder.iterdir():
            if movie.is_dir():
                # Try both the directory name and lowercase version
                reviews = movieReviews_memory.get(movie.name.lower(), [])
                print(f"DEBUG: Checking movie '{movie.name}' - found {len(reviews)} reviews")
                for review in reviews:
                    if review.user == username:
                        print(f"DEBUG: Found review by {username} for {movie.name}")
                        userReviews[movie.name] = {
                            "review": review.review,
                            "userRatingOutOf10": review.userRatingOutOf10,
                            "usefulnessVote": review.usefulnessVote,
                            "totalVotes": review.totalVotes
                        }
                        userReviews[movie.name]["metadata"] = loadMetadata(movie)
        print(f"DEBUG: Total reviews found for {username}: {len(userReviews)}")
        return userReviews
    
    def getLikedGenres(self,reviewList:Dict[str, Dict[str,Any]]) -> List[str]:
        """Get list of genres from user's reviewed movies - weighted by rating"""
        genreCount = {}
        for movieName in reviewList:
            metadata = reviewList[movieName]["metadata"]
            rating = reviewList[movieName]["userRatingOutOf10"]
            
            # Weight genres by rating (ratings >= 5 contribute, higher ratings contribute more)
            if rating >= 5:
                weight = rating - 4  # 5 gets weight 1, 10 gets weight 6
                genres = metadata.get('movieGenres', [])
                for genre in genres:
                    if genre in genreCount:
                        genreCount[genre] += weight
                    else:
                        genreCount[genre] = weight

        # Sort genres by weighted count and return top genres
        sortedGenres = sorted(genreCount.items(), key=lambda x: x[1], reverse=True)
        topGenres = [genre for genre, count in sortedGenres[:10]]  # Increased from 5 to 10
        print(f"DEBUG: Genre weights: {dict(sortedGenres)}")
        return topGenres 
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
    
        
    async def recommendMovies(self, username: str, numRecommendations: int = 5) -> List[Dict[str, Any]]:
        """Recommend movies based on user's review history"""
        print(f"DEBUG: recommendMovies called for user: {username}")
        userReviewHistory = self.getUserReviewHistory(username)
        print(f"DEBUG: userReviewHistory has {len(userReviewHistory)} movies")
        
        likedGenres = self.getLikedGenres(userReviewHistory)
        print(f"DEBUG: likedGenres: {likedGenres}")
        
        top5Movies = self.getTop5Movies(userReviewHistory)
        print(f"DEBUG: top5Movies: {top5Movies}")
        
        if not userReviewHistory:
            print(f"DEBUG: No review history found")
            return []  # No reviews, cannot recommend
        
        if not likedGenres:
            print(f"DEBUG: No liked genres, using all reviewed movies for content matching only")
        
        if not top5Movies:
            print(f"DEBUG: No top movies found")
            return []

        # Get all movies with metadata using the movies service
        allMovies = listMovies()
        
        # Enrich with TMDB posters before filtering
        print(f"DEBUG: Enriching {len(allMovies)} movies with TMDB posters for recommendations")
        allMovies = await enrich_movies_with_tmdb_posters_via_search(allMovies)
        
        # Filter out movies the user has already reviewed
        allOtherMovies = {}
        for movie in allMovies:
            movieTitle = movie.title  # Access Pydantic attribute
            # Check if user has reviewed this movie (case-insensitive)
            hasReviewed = any(
                movieTitle.lower() == reviewedMovie.lower() 
                for reviewedMovie in userReviewHistory.keys()
            )
            if not hasReviewed:
                # Convert Pydantic model to dict for easier processing
                allOtherMovies[movieTitle] = movie.model_dump()
        
        if not allOtherMovies:
            print(f"DEBUG: No unreviewed movies found. Total movies: {len(allMovies)}, reviewed: {len(userReviewHistory)}")
            return []  # No other movies to recommend
            
        topRateDescriptions = []
        for movie in top5Movies:
            try:
                topRateDescriptions.append(userReviewHistory[movie]["metadata"].get('description', ''))
            except Exception:
                continue
        
        descriptions = [allOtherMovies[movie].get('description', '') for movie in allOtherMovies.keys()]
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
            genreMatch = sum(1 for genre in metadata.get('movieGenres', []) if genre in likedGenres)/len(likedGenres) if likedGenres else 0

            #Score of 0-1 for a cosine similarity between movie descriptions
            contentMatch = float(similarities[idx]) if idx < len(similarities) else 0.0

            finalScore = (0.6 * genreMatch) + (0.4 * contentMatch)

            recommended.append({"title":metadata.get('title', movieName), "Match Score":finalScore, "Genre Score": genreMatch,"Content Score": contentMatch, "Metadata":metadata})

        recommended.sort(key=lambda x: x["Match Score"], reverse=True)
        return recommended[:numRecommendations]
            