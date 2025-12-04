from backend.routers.reviewRouter import movieReviews_memory

# Get admin2 reviews from memory
admin2_reviews = []
for movie_title, reviews_list in movieReviews_memory.items():
    for review in reviews_list:
        if review.user.lower() == 'admin2':
            admin2_reviews.append({
                'movie': movie_title,
                'rating': review.userRatingOutOf10,
                'title': review.reviewTitle
            })

print(f'Total admin2 reviews in memory: {len(admin2_reviews)}')
for rev in sorted(admin2_reviews, key=lambda x: x['movie']):
    print(f"  {rev['movie']}: {rev['rating']}/10 - {rev['title']}")
