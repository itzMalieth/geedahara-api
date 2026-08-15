from fastapi import APIRouter, Query
from app.services.search import get_songs_index

router = APIRouter()

@router.get("/")
def search_songs(
    q: str = Query(..., description="The search query (e.g. 'Mage Santhake' or 'Ajith')"),
    limit: int = Query(20, description="Max results to return")
):
    """
    Search for songs instantly using Meilisearch.
    """
    index = get_songs_index()
    # Meilisearch automatically searches across all searchable attributes
    results = index.search(q, {"limit": limit})
    return results
