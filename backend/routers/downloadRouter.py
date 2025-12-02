import csv
import json
from io import StringIO
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from backend.users.user import User

router = APIRouter()

@router.get("/my-reviews")
def downloadMyReviews(sessionToken: str, format: str = Query("json", pattern="^(json|csv)$")):
    """Download all reviews written by the current user in JSON or CSV format."""
    # Authenticate user
    current_user = User.getCurrentUser(sessionToken)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Import movieReviews_memory from reviewRouter (persistent reviews)
    from backend.routers.reviewRouter import movieReviews_memory
    
    # Collect all reviews by this user across all movies
    user_reviews = []
    
    for movie_title, reviews_list in movieReviews_memory.items():
        for review in reviews_list:
            if review.user.lower() == current_user.username.lower():
                user_reviews.append({
                    "movie_title": movie_title,
                    "date": review.dateOfReview,
                    "rating": review.userRatingOutOf10,
                    "review_title": review.reviewTitle,
                    "review_text": review.review,
                    "usefulness_votes": review.usefulnessVote,
                    "total_votes": review.totalVotes
                })
    
    if format == "json":
        # Return JSON
        content = json.dumps(user_reviews, indent=2)
        media_type = "application/json"
        filename = f"{current_user.username}_reviews.json"
    else:
        # Return CSV
        output = StringIO()
        if user_reviews:
            writer = csv.DictWriter(output, fieldnames=user_reviews[0].keys())
            writer.writeheader()
            writer.writerows(user_reviews)
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"{current_user.username}_reviews.csv"
    
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/my-lists")
def downloadMyLists(sessionToken: str, format: str = Query("json", pattern="^(json|csv)$")):
    """Download all movie lists created by the current user in JSON or CSV format."""
    # Authenticate user
    current_user = User.getCurrentUser(sessionToken)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Import userMovieLists from listsRouter
    from backend.routers.listsRouter import userMovieLists
    
    username_key = current_user.username.lower()
    user_lists = userMovieLists.get(username_key, {})
    
    if format == "json":
        # Return JSON with list names and movies
        content = json.dumps(user_lists, indent=2)
        media_type = "application/json"
        filename = f"{current_user.username}_lists.json"
    else:
        # Return CSV with flattened structure: list_name, movie_title
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["list_name", "movie_title"])
        
        for list_name, movies in user_lists.items():
            for movie_title in movies:
                writer.writerow([list_name, movie_title])
        
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"{current_user.username}_lists.csv"
    
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
