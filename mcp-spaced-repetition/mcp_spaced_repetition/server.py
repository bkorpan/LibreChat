#!/usr/bin/env python3
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import BaseModel, Field

from .models import Card, CardType, Review
from .fsrs import FSRS, Rating
from .storage import CardStorage


class SpacedRepetitionServer:
    def __init__(self):
        self.server = Server("mcp-spaced-repetition")
        self.storage: Optional[CardStorage] = None
        self.fsrs = FSRS()
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="add_card",
                    description="Add a new spaced repetition card",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "card_type": {
                                "type": "string",
                                "enum": ["fact", "concept"],
                                "description": "Type of card: 'fact' for Q&A pairs, 'concept' for AI-generated questions"
                            },
                            "question": {
                                "type": "string",
                                "description": "Question text (required for fact cards)"
                            },
                            "answer": {
                                "type": "string",
                                "description": "Answer text (required for fact cards)"
                            },
                            "concept": {
                                "type": "string",
                                "description": "Concept description (required for concept cards)"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional tags for organizing cards"
                            }
                        },
                        "required": ["card_type"]
                    }
                ),
                types.Tool(
                    name="remove_card",
                    description="Remove a card by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "card_id": {
                                "type": "string",
                                "description": "ID of the card to remove"
                            }
                        },
                        "required": ["card_id"]
                    }
                ),
                types.Tool(
                    name="get_next_due_card",
                    description="Get the next card due for review",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of due cards to return (default: 1)",
                                "default": 1
                            }
                        }
                    }
                ),
                types.Tool(
                    name="update_card",
                    description="Update the content of a card without affecting its schedule",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "card_id": {
                                "type": "string",
                                "description": "ID of the card to update"
                            },
                            "question": {
                                "type": "string",
                                "description": "Updated question (for fact cards)"
                            },
                            "answer": {
                                "type": "string",
                                "description": "Updated answer (for fact cards)"
                            },
                            "concept": {
                                "type": "string",
                                "description": "Updated concept (for concept cards)"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Updated tags for the card"
                            }
                        },
                        "required": ["card_id"]
                    }
                ),
                types.Tool(
                    name="review_card",
                    description="Review a card and reschedule it based on difficulty rating. Always ask the user to rate the difficulty: 1=Again (failed), 2=Hard, 3=Good, 4=Easy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "card_id": {
                                "type": "string",
                                "description": "ID of the card to review"
                            },
                            "rating": {
                                "type": "integer",
                                "description": "Difficulty rating: 1=Again, 2=Hard, 3=Good, 4=Easy",
                                "minimum": 1,
                                "maximum": 4
                            }
                        },
                        "required": ["card_id", "rating"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            if not self.storage:
                return [types.TextContent(type="text", text="Storage not initialized")]
            
            try:
                if name == "add_card":
                    result = await self._add_card(arguments or {})
                elif name == "remove_card":
                    result = await self._remove_card(arguments or {})
                elif name == "get_next_due_card":
                    result = await self._get_next_due_card(arguments or {})
                elif name == "update_card":
                    result = await self._update_card(arguments or {})
                elif name == "review_card":
                    result = await self._review_card(arguments or {})
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _add_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        card_type = CardType(args["card_type"])
        
        if card_type == CardType.FACT:
            if not args.get("question") or not args.get("answer"):
                return {"error": "Fact cards require both question and answer"}
            card = Card(
                card_type=card_type,
                question=args["question"],
                answer=args["answer"],
                tags=args.get("tags", [])
            )
        else:  # concept
            if not args.get("concept"):
                return {"error": "Concept cards require a concept description"}
            card = Card(
                card_type=card_type,
                concept=args["concept"],
                tags=args.get("tags", [])
            )
        
        # Initialize FSRS scheduling
        card.stability = self.fsrs.initial_stability
        card.difficulty = self.fsrs.initial_difficulty
        card.elapsed_days = 0
        card.scheduled_days = 0
        card.reps = 0
        card.lapses = 0
        card.state = "new"
        card.due = datetime.now(timezone.utc)
        
        await self.storage.add_card(card)
        return {"success": True, "card_id": card.id, "message": "Card added successfully"}
    
    async def _remove_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        card_id = args.get("card_id")
        if not card_id:
            return {"error": "card_id is required"}
        
        success = await self.storage.remove_card(card_id)
        if success:
            return {"success": True, "message": "Card removed successfully"}
        else:
            return {"error": "Card not found"}
    
    async def _get_next_due_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = args.get("limit", 1)
        cards = await self.storage.get_due_cards(limit)
        
        if not cards:
            return {"message": "No cards due for review"}
        
        result = []
        for card in cards:
            card_data = {
                "id": card.id,
                "card_type": card.card_type.value,
                "due": card.due.isoformat() if card.due else None,
                "state": card.state,
                "reps": card.reps,
                "lapses": card.lapses
            }
            
            if card.card_type == CardType.FACT:
                card_data["question"] = card.question
                card_data["answer"] = card.answer
            else:
                card_data["concept"] = card.concept
                card_data["ai_prompt"] = "Generate 2-3 varied, specific questions to test understanding of this concept. Ask different types of questions (definition, application, comparison, examples). Don't provide the answers - the user should answer them briefly to demonstrate comprehension."
            
            if card.tags:
                card_data["tags"] = card.tags
            
            result.append(card_data)
        
        return {"cards": result}
    
    async def _update_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        card_id = args.get("card_id")
        if not card_id:
            return {"error": "card_id is required"}
        
        card = await self.storage.get_card(card_id)
        if not card:
            return {"error": "Card not found"}
        
        updated_fields = []
        
        # Update card content based on card type
        if "question" in args and card.card_type == CardType.FACT:
            card.question = args["question"]
            updated_fields.append("question")
        if "answer" in args and card.card_type == CardType.FACT:
            card.answer = args["answer"]
            updated_fields.append("answer")
        if "concept" in args and card.card_type == CardType.CONCEPT:
            card.concept = args["concept"]
            updated_fields.append("concept")
        if "tags" in args:
            card.tags = args["tags"]
            updated_fields.append("tags")
        
        if not updated_fields:
            return {"error": "No valid fields to update"}
        
        await self.storage.update_card(card)
        
        return {
            "success": True,
            "message": f"Card updated successfully. Modified fields: {', '.join(updated_fields)}",
            "card_id": card_id
        }
    
    async def _review_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        card_id = args.get("card_id")
        if not card_id:
            return {"error": "card_id is required"}
        
        rating_value = args.get("rating")
        if not rating_value:
            return {"error": "rating is required"}
        
        card = await self.storage.get_card(card_id)
        if not card:
            return {"error": "Card not found"}
        
        try:
            rating = Rating(rating_value)
        except ValueError:
            return {"error": "Invalid rating. Must be 1 (Again), 2 (Hard), 3 (Good), or 4 (Easy)"}
        
        # Schedule next review using FSRS
        card = self.fsrs.review(card, rating)
        
        # Record review
        review = Review(
            card_id=card_id,
            rating=rating,
            reviewed_at=datetime.now(timezone.utc)
        )
        card.reviews.append(review)
        
        await self.storage.update_card(card)
        
        return {
            "success": True,
            "message": f"Card reviewed with rating {rating.value}",
            "next_due": card.due.isoformat() if card.due else None,
            "stability": card.stability,
            "difficulty": card.difficulty,
            "state": card.state,
            "interval_days": card.scheduled_days
        }
    
    async def run(self):
        # Get storage path from environment or use default
        storage_path = os.environ.get("SPACED_REPETITION_DATA_PATH", 
                                     str(Path.home() / ".mcp-spaced-repetition" / "cards.json"))
        
        self.storage = CardStorage(storage_path)
        await self.storage.initialize()
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-spaced-repetition",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def main():
    server = SpacedRepetitionServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()