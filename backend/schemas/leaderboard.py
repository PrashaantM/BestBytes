from pydantic import BaseModel, Field
from typing import Optional


class ReviewerStats(BaseModel):
    """Statistics for a single reviewer."""
    username: str
    totalReviews: int = Field(..., description="Total number of reviews written")
    totalUsefulnessVotes: int = Field(..., description="Sum of all usefulness votes received")
    averageUsefulnessRatio: float = Field(..., description="Average ratio of useful votes to total votes (0.0-1.0)")
    averageRating: float = Field(..., description="Average rating given by this reviewer (0.0-10.0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "MovieBuff123",
                "totalReviews": 42,
                "totalUsefulnessVotes": 1250,
                "averageUsefulnessRatio": 0.85,
                "averageRating": 7.5
            }
        }


class LeaderboardEntry(BaseModel):
    """A single entry in the leaderboard."""
    rank: int = Field(..., description="Position in the leaderboard (1-based)")
    username: str
    totalReviews: int
    totalUsefulnessVotes: int
    averageUsefulnessRatio: float
    helpfulnessScore: float = Field(..., description="Calculated score based on reviews and usefulness")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "username": "TopReviewer",
                "totalReviews": 100,
                "totalUsefulnessVotes": 5000,
                "averageUsefulnessRatio": 0.90,
                "helpfulnessScore": 4500.0
            }
        }
