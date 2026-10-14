"""
State definitions for the LangGraph Trip Planning Agent.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from data.schema import PaceLevel, PriceTier


class TravelSlots(BaseModel):
    destination: Optional[str] = None
    duration_days: Optional[int] = None
    month_or_dates: Optional[str] = None
    traveler_profile: Optional[str] = None  # Solo, Couple, Family, Friends
    vibe_preference: Optional[str] = None   # Heritage, Relaxed nature, Wildlife, Slow coastal
    pace: Optional[PaceLevel] = None        # leisure, balanced, explorer
    budget_tier: Optional[PriceTier] = None
    max_budget_inr: Optional[int] = None    # ₹30,000, ₹50,000, ₹100,000
    special_interests: List[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    day_number: int
    destination: str
    theme: str
    stay_name: str
    morning_activity: str
    afternoon_activity: Optional[str] = None
    sunset_evening_activity: Optional[str] = None
    dining_highlight: Optional[str] = None
    insider_advice: str


class GeneratedItinerary(BaseModel):
    circuit_name: str
    tagline: str
    total_days: int
    traveler_profile: str
    pace: str
    budget_tier: str = "Boutique Budget"
    max_budget_inr: Optional[int] = None
    estimated_total_cost_inr: int = 0
    cost_breakdown: Dict[str, int] = Field(default_factory=dict)
    stays_summary: List[Dict[str, Any]]
    recommended_hotels_by_hub: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    selected_stay_ids: Dict[str, str] = Field(default_factory=dict)
    days: List[DayPlan]
    why_personalized: str


class AgentState(BaseModel):
    messages: List[Dict[str, str]] = Field(default_factory=list)
    slots: TravelSlots = Field(default_factory=TravelSlots)
    circuit_id: Optional[str] = None
    itinerary: Optional[GeneratedItinerary] = None
    ready_for_itinerary: bool = False
    assistant_response: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
