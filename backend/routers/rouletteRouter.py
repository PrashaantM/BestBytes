from fastapi import APIRouter
from schemas.roulette import RouletteRequest, RouletteResponse
from services.rouletteService import get_random_movie, get_unique_genres

router = APIRouter(prefix="/roulette", tags=["roulette"])

@router.get("/genres")
def genres_list():
    return {"genres": get_unique_genres()}

@router.post("/spin", response_model=RouletteResponse)
def spin(req: RouletteRequest):
    movie = get_random_movie(req.genres)
    if movie is None:
        return {
            "title": "No match found",
            "movieIMDbRating": 0,
            "totalRatingCount": None,
            "totalUserReviews": None,
            "totalCriticReviews": None,
            "metaScore": None,
            "movieGenres": [],
            "directors": [],
            "datePublished": "",
            "creators": [],
            "mainStars": [],
            "description": "",
            "duration": 0
        }
    return movie
