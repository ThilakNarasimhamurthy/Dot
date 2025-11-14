"""
API routes for explanation endpoints
"""
from fastapi import APIRouter, Query
from datetime import datetime
from app.services.explanation import ExplanationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/explain", tags=["explain"])


@router.get("/hotspots")
async def explain_hotspots(limit: int = Query(5, ge=1, le=10)):
    """
    Generate natural language explanation of current traffic hotspots
    
    Args:
        limit: Number of top hotspots to include in explanation
    
    Returns:
        Explanation text and supporting data
    """
    try:
        service = ExplanationService()
        result = await service.explain_hotspots(limit=limit)
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in explain_hotspots endpoint: {e}", exc_info=True)
        return {
            "explanation": f"Traffic monitoring system is active. Unable to generate detailed summary at this moment. Error: {str(e)}",
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

