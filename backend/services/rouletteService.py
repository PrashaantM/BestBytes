from repositories.itemsRepo import loadMetadata, baseDir
import random
import os

def load_all_movies():
    movies = []
    for folder in os.listdir(baseDir):
        meta = loadMetadata(folder)
        if meta:
            movies.append(meta)
    return movies

def get_unique_genres():
    movies = load_all_movies()
    genre_set = set()
    for m in movies:
        for g in m.get("movieGenres", []):
            genre_set.add(g)
    return sorted(list(genre_set))

def spin_roulette(selected_genres):
    movies = load_all_movies()

    if not selected_genres:
        filtered = movies
    else:
        # Keep movies that match ANY of the genres user selected
        filtered = [m for m in movies if any(g in m.get("movieGenres", []) for g in selected_genres)]

    if not filtered:
        return {
            "movie": {},
            "found": False,
            "message": "No movies found for selected genres"
        }

    chosen = random.choice(filtered)
    return {
        "movie": chosen,
        "found": True
    }
