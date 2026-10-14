"""
Slot extraction module using Instructor + Gemini with fallback deterministic parsing.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from agent.state import TravelSlots
from data.schema import PaceLevel, PriceTier


def rule_based_extract(text: str, current_slots: TravelSlots) -> TravelSlots:
    """Deterministic extractor fallback or enhancement for robust slot-filling."""
    t = text.lower()
    slots = current_slots.model_copy()

    # Destination
    if any(k in t for k in ["rajasthan", "udaipur", "jodhpur", "jawai", "jaipur"]):
        slots.destination = "Rajasthan"
    elif any(k in t for k in ["kerala", "kochi", "munnar", "marari", "backwater"]):
        slots.destination = "Kerala"
    elif any(k in t for k in ["himachal", "tirthan", "jibhi", "kullu", "manali"]):
        slots.destination = "Himachal Pradesh"
    elif any(k in t for k in ["goa", "fontainhas", "aldona", "panjim"]):
        slots.destination = "Goa"
    elif any(k in t for k in ["meghalaya", "shillong", "cherrapunjee", "mawlynnong"]):
        slots.destination = "Meghalaya"
    elif any(k in t for k in ["kashmir", "srinagar", "pahalgam", "gulmarg", "dal lake", "nigeen"]):
        slots.destination = "Kashmir"
    elif any(k in t for k in ["ladakh", "leh", "nubra", "pangong", "monaster"]):
        slots.destination = "Ladakh"
    elif any(k in t for k in ["mumbai", "bombay", "alibaug"]):
        slots.destination = "Mumbai"

    # Duration
    dur_match = re.search(r'(\d+)\s*[-–]?\s*(?:days?|nights?|n\b|d\b)', t)
    if dur_match:
        slots.duration_days = int(dur_match.group(1))
    elif "a week" in t or "1 week" in t or "one week" in t:
        slots.duration_days = 7
    elif "weekend" in t or "long weekend" in t:
        slots.duration_days = 3

    # Traveler Profile
    if any(w in t for w in ["honeymoon", "anniversary", "couple", "wife", "husband", "partner", "girlfriend", "boyfriend"]):
        slots.traveler_profile = "Couple"
    elif any(w in t for w in ["solo", "myself", "alone"]):
        slots.traveler_profile = "Solo"
    elif any(w in t for w in ["family", "parents", "kids", "children"]):
        slots.traveler_profile = "Family"
    elif any(w in t for w in ["friends", "buddies", "gang", "group"]):
        slots.traveler_profile = "Friends"

    # Month / Season
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    for m in months:
        if m in t:
            slots.month_or_dates = m.capitalize()
            break
    if not slots.month_or_dates:
        if "winter" in t:
            slots.month_or_dates = "Winter (Nov-Feb)"
        elif "monsoon" in t:
            slots.month_or_dates = "Monsoon (Jul-Sep)"
        elif "spring" in t:
            slots.month_or_dates = "Spring (Feb-Apr)"

    # Pace
    if any(w in t for w in ["leisure", "slow", "relaxed", "peaceful", "unwind", "chill", "quiet", "no rush"]):
        slots.pace = PaceLevel.LEISURE
    elif any(w in t for w in ["packed", "explore", "adventure", "see everything", "active", "trek", "hike"]):
        slots.pace = PaceLevel.EXPLORER
    elif any(w in t for w in ["balanced", "moderate", "mix"]):
        slots.pace = PaceLevel.BALANCED

    # Vibe
    if any(w in t for w in ["heritage", "royal", "haveli", "palace", "history"]):
        slots.vibe_preference = "Heritage & Historic Stays"
    elif any(w in t for w in ["nature", "mountain", "hills", "pine", "forest", "cedar"]):
        slots.vibe_preference = "Mountain & Pine Forest Stays"
    elif any(w in t for w in ["beach", "coastal", "backwater", "river", "palm"]):
        slots.vibe_preference = "Slow Coastal & Waterways"
    elif any(w in t for w in ["bohemian", "art", "cafe", "architecture", "portuguese"]):
        slots.vibe_preference = "Bohemian & Architectural Stays"

    # Budget Cap & Tier
    if any(w in t for w in ["30,000", "30000", "30 k", "30k", "thirty thousand", "under 30", "within 30", "up to 30"]):
        slots.max_budget_inr = 30000
        slots.budget_tier = PriceTier.BOUTIQUE_BUDGET
    elif any(w in t for w in ["50,000", "50000", "50 k", "50k", "fifty thousand", "under 50", "within 50", "up to 50"]):
        slots.max_budget_inr = 50000
        slots.budget_tier = PriceTier.PREMIUM_CHARM
    elif any(w in t for w in ["1,00,000", "100000", "100k", "1 lakh", "1lakh", "1 lac", "1lac", "one lakh", "100,000", "lakh"]):
        slots.max_budget_inr = 100000
        slots.budget_tier = PriceTier.LUXURY_HERITAGE
    elif any(w in t for w in ["budget", "backpack", "hostel", "cheap", "affordable", "pocket-friendly"]):
        slots.max_budget_inr = 30000
        slots.budget_tier = PriceTier.BOUTIQUE_BUDGET
    elif any(w in t for w in ["luxury", "royal", "high-end", "5 star", "opulent"]):
        slots.max_budget_inr = 100000
        slots.budget_tier = PriceTier.LUXURY_HERITAGE
    elif any(w in t for w in ["boutique", "charm", "mid-range", "moderate"]):
        slots.max_budget_inr = 50000
        slots.budget_tier = PriceTier.PREMIUM_CHARM

    return slots


def extract_travel_slots(messages: List[Dict[str, str]], current_slots: TravelSlots) -> TravelSlots:
    """Extract slots using Gemini API if key is available, combined with rule-based extraction."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    # Accumulate all user text for context
    user_texts = [m["content"] for m in messages if m.get("role") == "user"]
    combined_user_text = " \n ".join(user_texts)

    slots = rule_based_extract(combined_user_text, current_slots)

    # Fast-track: If user tapped an option button or rule-based extraction extracted new details,
    # skip LLM network delay to make the conversation feel instantaneous!
    last_user_msg = user_texts[-1].lower() if user_texts else ""
    is_option_click = any(kw in last_user_msg for kw in [
        "couple", "family", "solo", "friends",
        "day", "days", "weekend", "week",
        "leisure", "balanced", "explorer", "slow", "active",
        "30,000", "50,000", "1 lakh", "30000", "50000", "100000", "budget", "luxury",
        "mumbai", "rajasthan", "himachal", "kashmir", "kerala", "goa", "ladakh", "meghalaya"
    ])
    if is_option_click and (slots.destination or slots.traveler_profile or slots.duration_days or slots.pace or slots.max_budget_inr):
        return slots

    if api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = f"""
            Analyze the following conversation between a traveler and an assistant:
            Conversation:
            {combined_user_text}

            Current known slots:
            {slots.model_dump_json()}

            Extract and update the following travel parameters:
            - destination: string (Indian region or state like Rajasthan, Kerala, Himachal Pradesh, Goa, Meghalaya, etc.)
            - duration_days: integer (number of days)
            - month_or_dates: string (month or specific travel window)
            - traveler_profile: string (e.g., Solo, Couple, Family, Friends)
            - vibe_preference: string (e.g., Heritage, Mountain retreat, Beach/Backwaters, Bohemian, Wildlife)
            - pace: string ("leisure", "balanced", "explorer")
            - budget_tier: string ("boutique_budget", "premium_charm", "luxury_heritage")
            - special_interests: list of strings (e.g. ["local food", "artisan crafts", "trout fishing"])
            """
            parsed = None
            for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TravelSlots,
                        ),
                    )
                    parsed = TravelSlots.model_validate_json(response.text)
                    break
                except Exception:
                    continue
            # Merge with high-confidence existing slots
            for field in TravelSlots.model_fields.keys():
                val = getattr(parsed, field)
                if val is not None and val != [] and val != "":
                    setattr(slots, field, val)
        except Exception as e:
            # Fallback cleanly to rule-based slots without failing
            print(f"[SlotExtractor] Gemini call fell back to rule-based engine: {e}")

    return slots
