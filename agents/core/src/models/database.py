# src/models/database.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskLevel(enum.Enum):
    HIGH = 'high'
    MEDIUM = 'medium' 
    # etc.
class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True)
    query = Column(String, nullable=False)
    time_window_hours = Column(Integer, nullable=False)
    analysis_types = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_level = Column(Enum(RiskLevel))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)