from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RouletteRequest(BaseModel):
    genres: List[str]

class RouletteResponse(BaseModel):
    movie: Dict[str, Any]
    found: bool
    message: Optional[str] = None
