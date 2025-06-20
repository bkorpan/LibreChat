import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiofiles
from pydantic import ValidationError

from .models import Card


class CardStorage:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.cards: dict[str, Card] = {}
    
    async def initialize(self):
        """Initialize storage, creating directory and loading existing data."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.storage_path.exists():
            await self._load_cards()
        else:
            await self._save_cards()
    
    async def _load_cards(self):
        """Load cards from JSON file."""
        try:
            async with aiofiles.open(self.storage_path, 'r') as f:
                data = await f.read()
                cards_data = json.loads(data)
                
                self.cards = {}
                for card_data in cards_data:
                    try:
                        card = Card.model_validate(card_data)
                        self.cards[card.id] = card
                    except ValidationError as e:
                        print(f"Error loading card: {e}")
        except Exception as e:
            print(f"Error loading cards file: {e}")
            self.cards = {}
    
    async def _save_cards(self):
        """Save cards to JSON file."""
        cards_data = [card.model_dump() for card in self.cards.values()]
        
        async with aiofiles.open(self.storage_path, 'w') as f:
            await f.write(json.dumps(cards_data, indent=2))
    
    async def add_card(self, card: Card) -> Card:
        """Add a new card to storage."""
        self.cards[card.id] = card
        await self._save_cards()
        return card
    
    async def get_card(self, card_id: str) -> Optional[Card]:
        """Get a card by ID."""
        return self.cards.get(card_id)
    
    async def update_card(self, card: Card) -> Card:
        """Update an existing card."""
        if card.id in self.cards:
            self.cards[card.id] = card
            await self._save_cards()
        return card
    
    async def remove_card(self, card_id: str) -> bool:
        """Remove a card by ID."""
        if card_id in self.cards:
            del self.cards[card_id]
            await self._save_cards()
            return True
        return False
    
    async def get_all_cards(self) -> List[Card]:
        """Get all cards."""
        return list(self.cards.values())
    
    async def get_due_cards(self, limit: int = 10) -> List[Card]:
        """Get cards that are due for review."""
        now = datetime.now(timezone.utc)
        due_cards = []
        
        for card in self.cards.values():
            # New cards are always due
            if card.state == "new" or (card.due and card.due <= now):
                due_cards.append(card)
        
        # Sort by due date (new cards first, then by due date)
        due_cards.sort(key=lambda c: (
            0 if c.state == "new" else 1,
            c.due or datetime.min.replace(tzinfo=timezone.utc)
        ))
        
        return due_cards[:limit]
    
    async def get_cards_by_tag(self, tag: str) -> List[Card]:
        """Get all cards with a specific tag."""
        return [card for card in self.cards.values() if tag in card.tags]