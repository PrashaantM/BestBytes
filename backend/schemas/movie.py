from pydantic import BaseModel, Field
from typing import List, Optional
from .movieReviews import movieReviews

class movie(BaseModel):
    title: str
    movieIMDbRating: float
    totalRatingCount: int
    totalUserReviews: str
    totalCriticReviews: str
    metaScore: str
    movieGenres: List[str]
    directors: List[str]
    datePublished: str
    creators: List[str]
    mainStars: List[str]
    description: str = Field(..., max_length=500)
    reviews: List[movieReviews] = []
    posterUrl: Optional[str] = None
    trailerUrl: Optional[str] = None
    seriesName: Optional[str] = None
    seriesOrder: Optional[int] = None

class movieCreate(BaseModel):
    title: str
    movieIMDbRating: float
    totalRatingCount: int
    totalUserReviews: str
    totalCriticReviews: str
    metaScore: str
    movieGenres: List[str]
    directors: List[str]
    datePublished: str
    creators: List[str]
    mainStars: List[str]
    description: str = Field(..., max_length=500)
    posterUrl: Optional[str] = None
    trailerUrl: Optional[str] = None
    seriesName: Optional[str] = None
    seriesOrder: Optional[int] = None

class movieUpdate(BaseModel):
    title: str
    movieIMDbRating: float
    totalRatingCount: int
    totalUserReviews: str
    totalCriticReviews: str
    metaScore: str
    movieGenres: List[str]
    directors: List[str]
    datePublished: str
    creators: List[str]
    mainStars: List[str]
    description: str = Field(..., max_length=500)
    posterUrl: Optional[str] = None
    trailerUrl: Optional[str] = None
    seriesName: Optional[str] = None
    seriesOrder: Optional[int] = None

class movieFilter(BaseModel):
    """
    Filter criteria for searching movies.
    
    Available genres: Action, Adventure, Comedy, Crime, Drama, Fantasy, Horror, Romance, Sci-Fi, Thriller
    """
    title: Optional[str] = Field(None, description="Partial movie title (case-insensitive)")
    searchField: Optional[str] = Field(None, description="Specific field to search: all, title, description, cast, director, creator")
    genres: Optional[List[str]] = Field(None, description="List of genres to filter by. Available: Action, Adventure, Comedy, Crime, Drama, Fantasy, Horror, Romance, Sci-Fi, Thriller")
    directors: Optional[List[str]] = Field(None, description="List of director names to filter by")
    min_rating: Optional[float] = Field(None, description="Minimum IMDb rating (0.0-10.0)", ge=0.0, le=10.0)
    max_rating: Optional[float] = Field(None, description="Maximum IMDb rating (0.0-10.0)", ge=0.0, le=10.0)
    year: Optional[int] = Field(None, description="Filter by year in release date")