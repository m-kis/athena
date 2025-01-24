from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.repositories.analysis_repository import AnalysisRepository
from typing import List
from src.config.database import get_session

router = APIRouter()

@router.get("/history/recent")
async def get_recent_analyses(limit: int = 10, session: Session = Depends(get_session)):
    repo = AnalysisRepository(session)
    return await repo.get_recent(limit)

@router.get("/history/trends")
async def get_trends(days: int = 7, session: Session = Depends(get_session)):
    repo = AnalysisRepository(session)
    return await repo.get_trends(days)