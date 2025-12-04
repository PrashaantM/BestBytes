from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.tmdbService import search_tmdb, get_tmdb_movie_details

router = APIRouter()

class SearchBody(BaseModel):
    query: str
    page: int = 1

@router.post("/tmdb/search")
async def tmdb_search(body: SearchBody):
    try:
        results = await search_tmdb(body.query, body.page)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tmdb/{tmdb_id}")
async def tmdb_details(tmdb_id: int):
    try:
        details = await get_tmdb_movie_details(tmdb_id)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
