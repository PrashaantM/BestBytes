#!/usr/bin/env python3
import sys
sys.path.insert(0, ".")

from backend.routers.reviewRouter import movieReviews_memory

admin2_count = 0
admin2_reviews = []
for movie, reviews in movieReviews_memory.items():
    for review in reviews:
        if review.user.lower() == "admin2":
            admin2_count += 1
            admin2_reviews.append((movie, review.userRatingOutOf10, review.reviewTitle))

print(f"Total admin2 reviews in memory: {admin2_count}")
for movie, rating, title in sorted(admin2_reviews):
    print(f"  {movie}: {rating}/10 - {title}")
