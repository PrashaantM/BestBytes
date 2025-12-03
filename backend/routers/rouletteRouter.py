from fastapi import APIRouter
from schemas.roulette import RouletteRequest, RouletteResponse
from services.rouletteService import spin_roulette, get_unique_genres

router = APIRouter(prefix="/roulette", tags=["Movie Roulette"])

@router.get("/genres")
def list_genres():
    return {"genres": get_unique_genres()}

@router.post("/spin", response_model=RouletteResponse)
def spin(req: RouletteRequest):
    result = spin_roulette(req.genres)
    
    if not result["found"]:
        return {
            "movie": {},
            "found": False,
            "message": result.get("message")
        }

    return {
        "movie": result["movie"],
        "found": True
    }
