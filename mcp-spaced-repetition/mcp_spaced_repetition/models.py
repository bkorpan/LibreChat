from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CardType(str, Enum):
    FACT = "fact"
    CONCEPT = "concept"


class Rating(int, Enum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


class Review(BaseModel):
    card_id: str
    rating: Rating
    reviewed_at: datetime


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    card_type: CardType
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    
    # Content fields
    question: Optional[str] = None  # For fact cards
    answer: Optional[str] = None    # For fact cards
    concept: Optional[str] = None   # For concept cards
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    
    # FSRS scheduling fields
    due: Optional[datetime] = None
    stability: float = 0.0
    difficulty: float = 0.0
    elapsed_days: float = 0.0
    scheduled_days: float = 0.0
    reps: int = 0
    lapses: int = 0
    state: str = "new"  # new, learning, review, relearning
    last_review: Optional[datetime] = None
    
    # Review history
    reviews: List[Review] = Field(default_factory=list)
    
    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Convert datetime objects to ISO format strings for JSON serialization
        for field in ['created_at', 'due', 'last_review']:
            if field in data and data[field]:
                data[field] = data[field].isoformat()
        
        # Convert reviews
        if 'reviews' in data:
            for review in data['reviews']:
                if 'reviewed_at' in review:
                    review['reviewed_at'] = review['reviewed_at'].isoformat()
        
        return data
    
    @classmethod
    def model_validate(cls, obj):
        # Convert ISO format strings back to datetime objects
        if isinstance(obj.get('created_at'), str):
            obj['created_at'] = datetime.fromisoformat(obj['created_at'])
        if isinstance(obj.get('due'), str):
            obj['due'] = datetime.fromisoformat(obj['due'])
        if isinstance(obj.get('last_review'), str):
            obj['last_review'] = datetime.fromisoformat(obj['last_review'])
        
        # Convert reviews
        if 'reviews' in obj:
            for review in obj['reviews']:
                if isinstance(review.get('reviewed_at'), str):
                    review['reviewed_at'] = datetime.fromisoformat(review['reviewed_at'])
        
        return super().model_validate(obj)