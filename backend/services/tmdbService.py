import os
import httpx
from typing import Dict, List, Optional

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

def _get_api_key() -> str:
    key = os.getenv("TMDB_API_KEY", "")
    if not key:
        raise RuntimeError("TMDB_API_KEY not set in environment")
    return key

async def search_tmdb(query: str, page: int = 1) -> List[Dict]:
    params = {"query": query, "page": page, "include_adult": False}
    headers = {"Authorization": f"Bearer {_get_api_key()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{TMDB_BASE}/search/movie", params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        results = []
        for m in data.get("results", []):
            results.append({
                "id": m.get("id"),
                "title": m.get("title"),
                "releaseDate": m.get("release_date"),
                "voteAverage": m.get("vote_average"),
                "overview": m.get("overview"),
                "posterUrl": f"{TMDB_IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            })
        return results

async def get_popular_movies(page: int = 1) -> List[Dict]:
    """Fetch popular movies from TMDB."""
    params = {"page": page, "include_adult": False}
    headers = {"Authorization": f"Bearer {_get_api_key()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{TMDB_BASE}/movie/popular", params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        results = []
        for m in data.get("results", []):
            results.append({
                "id": m.get("id"),
                "title": m.get("title"),
                "releaseDate": m.get("release_date"),
                "voteAverage": m.get("vote_average"),
                "overview": m.get("overview"),
                "posterUrl": f"{TMDB_IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            })
        return results

async def get_tmdb_movie_details(tmdb_id: int) -> Dict:
    headers = {"Authorization": f"Bearer {_get_api_key()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Fetch details and videos sequentially
        details = await client.get(f"{TMDB_BASE}/movie/{tmdb_id}", headers=headers)
        details.raise_for_status()
        videos = await client.get(f"{TMDB_BASE}/movie/{tmdb_id}/videos", headers=headers)
        videos.raise_for_status()
        d = details.json()
        v = videos.json()

        # Find a YouTube trailer if available
        trailer_url: Optional[str] = None
        for vid in v.get("results", []):
            if vid.get("site") == "YouTube" and vid.get("type") in ("Trailer", "Teaser"):
                key = vid.get("key")
                if key:
                    trailer_url = f"https://www.youtube.com/watch?v={key}"
                    break

        return {
            "id": d.get("id"),
            "title": d.get("title"),
            "overview": d.get("overview"),
            "genres": [g.get("name") for g in d.get("genres", [])],
            "releaseDate": d.get("release_date"),
            "runtime": d.get("runtime"),
            "voteAverage": d.get("vote_average"),
            "posterUrl": f"{TMDB_IMG_BASE}{d['poster_path']}" if d.get("poster_path") else None,
            "backdropUrl": f"https://image.tmdb.org/t/p/w780{d['backdrop_path']}" if d.get("backdrop_path") else None,
            "trailerUrl": trailer_url,
        }
