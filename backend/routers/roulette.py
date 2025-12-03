from pydantic import BaseModel
from typing import List, Optional

class RouletteRequest(BaseModel):
    genres: List[str]

class RouletteResponse(BaseModel):
    title: str
    movieIMDbRating: float
    totalRatingCount: Optional[str]
    totalUserReviews: Optional[str]
    totalCriticReviews: Optional[str]
    metaScore: Optional[str]
    movieGenres: List[str]
    directors: List[str]
    datePublished: str
    creators: List[str]
    mainStars: List[str]
    description: str
    duration: int
    durationMinutes: Optional[int] = None
