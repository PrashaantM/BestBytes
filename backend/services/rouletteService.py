import os
import json
import random

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")



def load_all_movies():
    movies = []
    for movie_folder in os.listdir(DATA_DIR):
        movie_path = os.path.join(DATA_DIR, movie_folder, "metadata.json")
        if os.path.exists(movie_path):
            try:
                with open(movie_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    movies.append(metadata)
            except:
                pass
    return movies




def get_unique_genres():
    movies = load_all_movies()
    genre_set = set()
    for movie in movies:
        for g in movie.get("movieGenres", []):
            genre_set.add(g)
    return sorted(list(genre_set))




def get_random_movie(selected_genres):
    movies = load_all_movies()
    if not selected_genres:
        filtered = movies
    else:
        filtered = [
            m for m in movies if any(g in m.get("movieGenres", []) for g in selected_genres)
        ]

    if not filtered:
        return None

    choice = random.choice(filtered)
    choice["durationMinutes"] = choice.get("duration")
    return choice
