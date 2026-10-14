"""
Data models and schemas for the Curated India Trip Planner dataset.
"""

from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field


class VibeCategory(str, Enum):
    HERITAGE_ROYAL = "heritage_royal"
    MOUNTAIN_SERENE = "mountain_serene"
    SLOW_COASTAL = "slow_coastal"
    FOREST_WILDLIFE = "forest_wildlife"
    OFFBEAT_CULTURAL = "offbeat_cultural"
    BOHEMIAN_ARTISTIC = "bohemian_artistic"


class PaceLevel(str, Enum):
    LEISURE = "leisure"         # 1-2 activities/day, late starts
    BALANCED = "balanced"       # 2-3 activities/day
    EXPLORER = "explorer"       # 3-4 activities/day, active exploration


class PriceTier(str, Enum):
    BOUTIQUE_BUDGET = "boutique_budget"   # ₹3,500 - ₹7,000 / night
    PREMIUM_CHARM = "premium_charm"       # ₹7,500 - ₹15,000 / night
    LUXURY_HERITAGE = "luxury_heritage"   # ₹16,000 - ₹35,000+ / night


class CuratedStay(BaseModel):
    id: str
    name: str
    circuit_id: str
    destination: str
    neighborhood: str
    price_tier: PriceTier
    approx_price_per_night_inr: int
    price_range: str = ""
    image_url: str = "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    food_available: bool = True
    food_details: str = "In-house authentic dining available"
    breakfast_available: bool = True
    breakfast_details: str = "Complimentary artisanal breakfast included"
    wifi_available: bool = True
    wifi_details: str = "High-speed Wi-Fi available"
    vibe_tags: List[VibeCategory]
    stay_type: str  # e.g., "18th-century Haveli", "Plantation Bungalow", "Pine Wood Cottage"
    why_special: str
    best_for: List[str]  # ["couples", "solo", "architecture-lovers", "honeymoon"]
    highlight_amenities: List[str]
    booking_advice: str


class CuratedActivity(BaseModel):
    id: str
    destination: str
    circuit_id: str
    title: str
    time_slot: str  # "morning", "afternoon", "sunset", "evening"
    duration_hours: float
    pace_suitability: List[PaceLevel]
    category: str   # "culinary", "artisan_craft", "nature_walk", "architecture", "hidden_viewpoint"
    description: str
    insider_tip: str
    is_offbeat: bool = True


class DiningSpot(BaseModel):
    id: str
    destination: str
    name: str
    cuisine_type: str
    vibe: str
    must_try: str
    price_for_two_inr: int


class CircuitRoute(BaseModel):
    circuit_id: str
    circuit_name: str
    region: str
    ideal_duration_days: List[int]  # [min_days, max_days]
    best_months: List[str]
    hubs: List[str]  # e.g. ["Udaipur", "Jawai", "Jodhpur"]
    transfer_logistics: Dict[str, str]
    tagline: str


class CuratedIndiaDataset(BaseModel):
    circuits: List[CircuitRoute]
    stays: List[CuratedStay]
    activities: List[CuratedActivity]
    dining: List[DiningSpot]
