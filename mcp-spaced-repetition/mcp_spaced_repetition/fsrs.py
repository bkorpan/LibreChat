"""
FSRS (Free Spaced Repetition Scheduler) Algorithm Implementation
Based on: https://github.com/open-spaced-repetition/py-fsrs
"""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import Card, Rating


class FSRS:
    def __init__(
        self,
        w: Optional[list[float]] = None,
        enable_fuzz: bool = False,
        maximum_interval: int = 36500,
        desired_retention: float = 0.9,
    ):
        # Default parameters from FSRS-4.5
        self.w = w or [
            0.4072, 1.1829, 3.1262, 15.4722,
            7.2102, 0.5316, 1.0651, 0.0234,
            1.616, 0.1544, 1.0824, 1.9813,
            0.0953, 0.2975, 2.2042, 0.2407,
            2.9466, 0.5034, 0.6567
        ]
        self.enable_fuzz = enable_fuzz
        self.maximum_interval = maximum_interval
        self.desired_retention = desired_retention
        
        # Initial values
        self.initial_stability = 0.5
        self.initial_difficulty = 5.0
    
    def review(self, card: Card, rating: Rating) -> Card:
        """Process a review and update the card's scheduling parameters."""
        now = datetime.now(timezone.utc)
        
        if card.last_review:
            elapsed_days = (now - card.last_review).total_seconds() / 86400
        else:
            elapsed_days = 0
        
        card.elapsed_days = elapsed_days
        card.last_review = now
        card.reps += 1
        
        # Update state based on rating
        if card.state == "new":
            card.state = "learning" if rating < Rating.EASY else "review"
        elif rating == Rating.AGAIN:
            card.state = "relearning"
            card.lapses += 1
        
        # Calculate new parameters
        if card.state == "new" or card.reps == 1:
            card.stability = self._init_stability(rating)
            card.difficulty = self._init_difficulty(rating)
        else:
            card.difficulty = self._next_difficulty(card.difficulty, rating)
            card.stability = self._next_stability(
                card.stability, 
                card.difficulty, 
                rating, 
                elapsed_days
            )
        
        # Calculate interval
        interval = self._next_interval(card.stability, rating)
        card.scheduled_days = min(interval, self.maximum_interval)
        
        # Apply fuzz if enabled
        if self.enable_fuzz and card.state == "review":
            card.scheduled_days = self._apply_fuzz(card.scheduled_days)
        
        # Set next due date
        card.due = now + timedelta(days=card.scheduled_days)
        
        return card
    
    def _init_stability(self, rating: Rating) -> float:
        """Initialize stability for a new card."""
        return self.w[rating.value - 1]
    
    def _init_difficulty(self, rating: Rating) -> float:
        """Initialize difficulty for a new card."""
        return max(1, min(10, self.w[4] - (rating.value - 3) * self.w[5]))
    
    def _next_difficulty(self, d: float, rating: Rating) -> float:
        """Calculate next difficulty."""
        next_d = d - self.w[6] * (rating.value - 3)
        return max(1, min(10, self._mean_reversion(self.w[4], next_d)))
    
    def _mean_reversion(self, init: float, current: float) -> float:
        """Apply mean reversion to a parameter."""
        return self.w[7] * init + (1 - self.w[7]) * current
    
    def _next_stability(self, s: float, d: float, rating: Rating, elapsed_days: float) -> float:
        """Calculate next stability."""
        # Recall rate
        retrievability = math.exp(-elapsed_days / s)
        
        # Stability increase factor
        if rating == Rating.AGAIN:
            s_recall = self.w[11] * math.pow(d, -self.w[12]) * \
                       (math.pow(s + 1, self.w[13]) - 1) * \
                       math.exp(-retrievability * self.w[14])
            next_s = s * (1 + s_recall * self.w[15])
        elif rating == Rating.HARD:
            next_s = s * (1 + math.exp(self.w[8]) * 
                         (11 - d) * 
                         math.pow(s, -self.w[9]) * 
                         (math.exp((1 - retrievability) * self.w[10]) - 1) * 
                         self.w[16])
        elif rating == Rating.GOOD:
            next_s = s * (1 + math.exp(self.w[8]) * 
                         (11 - d) * 
                         math.pow(s, -self.w[9]) * 
                         (math.exp((1 - retrievability) * self.w[10]) - 1))
        else:  # EASY
            next_s = s * (1 + math.exp(self.w[8]) * 
                         (11 - d) * 
                         math.pow(s, -self.w[9]) * 
                         (math.exp((1 - retrievability) * self.w[10]) - 1) * 
                         self.w[17])
        
        return max(0.1, next_s)
    
    def _next_interval(self, stability: float, rating: Rating) -> float:
        """Calculate the next review interval in days."""
        if rating == Rating.AGAIN:
            # Short interval for failed cards
            return max(1, stability * 0.2)
        else:
            # Calculate interval based on desired retention
            return stability * (1 / self.desired_retention - 1)
    
    def _apply_fuzz(self, interval: float) -> float:
        """Apply fuzzing to prevent cards from clustering."""
        # Simple fuzzing: ±5% randomization
        import random
        min_interval = int(interval * 0.95)
        max_interval = int(interval * 1.05)
        return random.randint(min_interval, max_interval)