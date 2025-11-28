from typing import List, Dict
from collections import defaultdict
from backend.schemas.leaderboard import ReviewerStats, LeaderboardEntry


def calculateReviewerStats(reviews_by_movie: Dict[str, List]) -> Dict[str, ReviewerStats]:
    """
    Calculate statistics for all reviewers based on their reviews.
    
    Args:
        reviews_by_movie: Dictionary mapping movie titles to lists of reviews
        
    Returns:
        Dictionary mapping usernames to their ReviewerStats
    """
    stats: Dict[str, dict] = defaultdict(lambda: {
        "totalReviews": 0,
        "totalUsefulnessVotes": 0,
        "totalVotes": 0,
        "totalRating": 0.0
    })
    
    # Aggregate data for each reviewer
    for reviews in reviews_by_movie.values():
        for review in reviews:
            username = review.user.lower()
            stats[username]["totalReviews"] += 1
            stats[username]["totalUsefulnessVotes"] += review.usefulnessVote
            stats[username]["totalVotes"] += review.totalVotes
            stats[username]["totalRating"] += review.userRatingOutOf10
    
    # Convert to ReviewerStats objects
    reviewer_stats = {}
    for username, data in stats.items():
        average_ratio = (
            data["totalUsefulnessVotes"] / data["totalVotes"] 
            if data["totalVotes"] > 0 else 0.0
        )
        average_rating = (
            data["totalRating"] / data["totalReviews"] 
            if data["totalReviews"] > 0 else 0.0
        )
        
        reviewer_stats[username] = ReviewerStats(
            username=username,
            totalReviews=data["totalReviews"],
            totalUsefulnessVotes=data["totalUsefulnessVotes"],
            averageUsefulnessRatio=round(average_ratio, 4),
            averageRating=round(average_rating, 2)
        )
    
    return reviewer_stats


def calculateHelpfulnessScore(stats: ReviewerStats) -> float:
    """
    Calculate a helpfulness score for a reviewer.
    
    Formula: (total_usefulness_votes * usefulness_ratio) + (total_reviews * 10)
    This rewards both quantity and quality of reviews.
    """
    base_score = stats.totalUsefulnessVotes * stats.averageUsefulnessRatio
    review_bonus = stats.totalReviews * 10
    return round(base_score + review_bonus, 2)


def generateLeaderboard(
    reviews_by_movie: Dict[str, List],
    limit: int = 10,
    min_reviews: int = 1
) -> List[LeaderboardEntry]:
    """
    Generate a leaderboard of top reviewers.
    
    Args:
        reviews_by_movie: Dictionary mapping movie titles to lists of reviews
        limit: Maximum number of entries to return
        min_reviews: Minimum number of reviews required to be on leaderboard
        
    Returns:
        List of LeaderboardEntry objects, sorted by helpfulness score
    """
    # Calculate stats for all reviewers
    reviewer_stats = calculateReviewerStats(reviews_by_movie)
    
    # Filter by minimum reviews and calculate scores
    leaderboard_data = []
    for username, stats in reviewer_stats.items():
        if stats.totalReviews >= min_reviews:
            score = calculateHelpfulnessScore(stats)
            leaderboard_data.append({
                "username": username,
                "stats": stats,
                "score": score
            })
    
    # Sort by score (descending)
    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
    
    # Create leaderboard entries with ranks
    leaderboard = []
    for rank, data in enumerate(leaderboard_data[:limit], start=1):
        stats = data["stats"]
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            username=stats.username,
            totalReviews=stats.totalReviews,
            totalUsefulnessVotes=stats.totalUsefulnessVotes,
            averageUsefulnessRatio=stats.averageUsefulnessRatio,
            helpfulnessScore=data["score"]
        ))
    
    return leaderboard
