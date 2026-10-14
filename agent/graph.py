"""
LangGraph state machine coordinating extraction, clarification, and itinerary generation.
Powered by Google Gemini API with structured clarification option buttons.
"""

import os
from pathlib import Path
from typing import Literal, Dict, Any, List, Tuple
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from agent.state import AgentState, TravelSlots
from agent.extractor import extract_travel_slots
from agent.composer import compose_grounded_itinerary
from data.db import TravelDatabase


class GeminiClarificationOutput(BaseModel):
    response_text: str = Field(description="Conversational response acknowledging traveler and asking 1-2 focused questions")
    options: List[str] = Field(default_factory=list, description="3 to 4 short, distinct clickable option button labels matching the question, e.g. ['👫 Couple Heritage Exploration', '👨‍👩‍👧 Family Adventure', '🎒 Solo Retreat', '👥 Friends Getaway']")


def node_extract(state: AgentState) -> Dict[str, Any]:
    """Node 1: Extract and accumulate travel slots from conversational messages."""
    updated_slots = extract_travel_slots(state.messages, state.slots)
    db = TravelDatabase.get_instance()
    circuit = None
    if updated_slots.destination:
        circuit = db.find_circuit_by_query(updated_slots.destination)

    # Check if mandatory slots are present
    has_dest = bool(updated_slots.destination)
    has_dur = bool(updated_slots.duration_days)
    has_traveler = bool(updated_slots.traveler_profile)
    has_budget = bool(updated_slots.max_budget_inr or updated_slots.budget_tier)
    has_vibe_or_pace = bool(updated_slots.pace or updated_slots.vibe_preference)

    # Ready if destination + duration + traveler + budget + pace/vibe are known
    ready = has_dest and has_dur and has_traveler and has_budget and has_vibe_or_pace

    return {
        "slots": updated_slots,
        "circuit_id": circuit.circuit_id if circuit else None,
        "ready_for_itinerary": ready
    }


def router_decision(state: AgentState) -> Literal["ask_clarification", "compose_itinerary"]:
    """Decide whether to clarify missing details or build the itinerary."""
    if state.ready_for_itinerary:
        return "compose_itinerary"
    return "ask_clarification"


def compute_fallback_options(missing: List[str], slots: TravelSlots) -> List[str]:
    """Compute relevant clickable option pills based on what context is missing."""
    if not slots.destination:
        return [
            "🏰 Rajasthan Heritage Trail",
            "🌴 Kerala Slow Living",
            "🏔️ Himachal Alpine Woods",
            "🛶 Kashmir Valley & Lakes",
            "🌌 Ladakh High Passes",
            "🏛️ Mumbai Art Deco & Coast",
            "🎨 Goan Susegad Hinterland"
        ]

    missing_str = " ".join(missing).lower()

    if "traveler profile" in missing_str:
        return [
            "👫 Couple Heritage Exploration",
            "👨‍👩‍👧 Family Coastal Adventure",
            "🎒 Solo Culture Retreat",
            "👥 Friends Weekend Getaway"
        ]
    elif "pace" in missing_str:
        return [
            "🌸 Leisure Pace (Slow & Relaxed)",
            "⚖️ Balanced Pace (Curated Highlights)",
            "🥾 Explorer Pace (Active Hikes)"
        ]
    elif "duration" in missing_str:
        return [
            "3 Days (Long Weekend)",
            "5 Days (Curated Circuit)",
            "7 Days (Deep Immersion)"
        ]

    return [
        "👫 Couple Travel",
        "👨‍👩‍👧 Family Travel",
        "🌸 Leisure Pace",
        "🥾 Active Explorer"
    ]


def call_gemini_for_clarification(messages: List[Dict[str, str]], slots: TravelSlots, missing: List[str]) -> Tuple[str, List[str]]:
    """Use Gemini to craft an empathetic clarification question AND clickable option buttons."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return None, []

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
        db = TravelDatabase.get_instance()
        circuits_summary = "\n".join([f"- {c.circuit_name} ({c.region}): {c.tagline}" for c in db.dataset.circuits])

        prompt = f"""
        You are the Antigravity Curated India Travel Consultant AI.
        Unlike generic agents that recommend standard commercial hotels, you specialize in characterful stays (restored Rajput havelis, tea-estate planter bungalows, riverside pine chalets, Nigeen Lake cedar houseboats, Mumbai heritage Art Deco townhouses) and authentic local experiences.

        Conversation history:
        {history_text}

        Currently known travel parameters:
        {slots.model_dump_json()}

        Missing information needed to build the bespoke itinerary:
        {', '.join(missing)}

        Available Curated Circuits in our portfolio:
        {circuits_summary}

        Instructions:
        1. Acknowledge what the user said with warmth, excitement, and deep taste in Indian travel.
        2. Ask 1 or 2 focused questions to collect the missing details ({', '.join(missing)}).
        3. Keep your response_text concise (2-3 short paragraphs max), elegant, and friendly.
        4. CRITICAL: Provide 3 to 4 distinct, clickable option button labels in `options` that directly answer your question so the user can just tap a button without typing!
           Examples of good options:
           - For traveler/vibe: ["👫 Couple Heritage Exploration", "👨‍👩‍👧 Family Adventure", "🎒 Solo Architecture Retreat", "👥 Friends Getaway"]
           - For pace: ["🌸 Leisure Pace (Slow & Relaxed)", "⚖️ Balanced Pace", "🥾 Active Explorer"]
           - For duration: ["3 Days (Weekend)", "5 Days (Curated)", "7 Days (Complete)"]
        """
        for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiClarificationOutput,
                    )
                )
                parsed = GeminiClarificationOutput.model_validate_json(response.text)
                if parsed.response_text:
                    opts = parsed.options if parsed.options else compute_fallback_options(missing, slots)
                    return parsed.response_text.strip(), opts
            except Exception:
                continue
    except Exception as e:
        print(f"[Gemini Clarification Error]: {e}")
    return None, []


def call_gemini_for_narrative(messages: List[Dict[str, str]], itinerary: Any) -> str:
    """Use Gemini to write an inspiring, personalized narrative explaining the grounded itinerary."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages[-4:]])
        stays_text = "\n".join([f"- {s['stay_name']} ({s['hub']}): {s['stay_type']} - {s['why_special']} ({s['price_approx']})" for s in itinerary.stays_summary])
        
        prompt = f"""
        You are the Antigravity Curated India Travel Consultant AI.
        You have successfully assembled a bespoke itinerary for the traveler from our verified catalog.

        Recent conversation context:
        {history_text}

        Curated Itinerary Details:
        - Circuit: {itinerary.circuit_name} ({itinerary.total_days} Days)
        - Tagline: {itinerary.tagline}
        - Traveler Profile: {itinerary.traveler_profile}
        - Pace: {itinerary.pace}
        - Target Budget Cap: ₹{itinerary.max_budget_inr:,} if itinerary.max_budget_inr else 'Not capped'
        - Total Estimated Cost: ₹{itinerary.estimated_total_cost_inr:,}
        - Cost Breakdown: {itinerary.cost_breakdown}

        Handpicked Stays from Catalog:
        {stays_text}

        Instructions:
        1. Present this personalized plan with warmth, sophistication, and enthusiasm.
        2. Explain specifically WHY these exact stays and activities were chosen based on what the traveler asked for.
        3. Highlight the handpicked authentic stays ({', '.join(s['stay_name'] for s in itinerary.stays_summary)}).
        4. If the traveler specified a budget (especially ₹30,000), explicitly reassure them that the total estimated package cost (₹{itinerary.estimated_total_cost_inr:,}) is strictly within their ₹{itinerary.max_budget_inr:,} budget limit.
        5. Inform the user that they are NOT locked into a single hotel — multiple candidate properties with real photos, pricing ranges, in-house food availability, breakfast, and Wi-Fi status are available to browse and pick in the '🏨 Hotel Recommendations' tab below.
        6. Mention that the full interactive day-by-day breakdown, cost breakdown, and stay details are rendered below in the visual tabs.
        7. CRITICAL: Strictly mention ONLY the stays listed above. Never invent generic hotels like Taj, Marriott, or Oberoi.
        """
        for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text and len(response.text.strip()) > 20:
                    return response.text.strip()
            except Exception:
                continue
    except Exception as e:
        print(f"[Gemini Narrative Error]: {e}")
    return None


def node_ask_clarification(state: AgentState) -> Dict[str, Any]:
    """Node 2: Instant, pre-fed clarification questions with clickable option buttons (zero network delay)."""
    slots = state.slots

    # 1. Missing Destination (if not mentioned in prompt)
    if not slots.destination:
        msg = (
            "Namaste! 🙏 Welcome to your **Curated India AI Travel Planner**.\n\n"
            "Where in India would you like to travel? Choose one of our signature circuits below, or type any destination:"
        )
        opts = [
            "🏛️ Mumbai Art Deco & Coast",
            "🏰 Rajasthan Heritage Trail",
            "🏔️ Himachal Alpine Woods",
            "🛶 Kashmir Valley & Lakes",
            "🌴 Kerala Backwaters & Tea",
            "🌌 Ladakh High Passes",
            "🎨 Goan Susegad Hinterland",
            "☁️ Meghalaya Cloud Forests"
        ]
        return {
            "assistant_response": msg,
            "clarification_options": opts,
            "messages": state.messages + [{"role": "assistant", "content": msg}]
        }

    # 2. Missing Traveler Profile (if not mentioned in prompt)
    if not slots.traveler_profile:
        msg = (
            f"Great choice! Planning your journey for **{slots.destination}**.\n\n"
            "**Who will be traveling with you, or what is the focus of this trip?**"
        )
        opts = [
            "👫 Couple / Romantic",
            "👨‍👩‍👧 Family with Kids",
            "🎒 Solo Retreat",
            "👥 Friends Getaway"
        ]
        return {
            "assistant_response": msg,
            "clarification_options": opts,
            "messages": state.messages + [{"role": "assistant", "content": msg}]
        }

    # 3. Missing Duration (if not mentioned in prompt)
    if not slots.duration_days:
        traveler_str = f" for a **{slots.traveler_profile}**" if slots.traveler_profile else ""
        msg = f"Wonderful! **How many days do you have in mind for {slots.destination}{traveler_str}?**"
        opts = [
            "3 Days (Weekend Getaway)",
            "5 Days (Curated Circuit)",
            "7 Days (Complete Immersion)"
        ]
        return {
            "assistant_response": msg,
            "clarification_options": opts,
            "messages": state.messages + [{"role": "assistant", "content": msg}]
        }

    # 4. Missing Budget (if not mentioned in prompt)
    if not (slots.max_budget_inr or slots.budget_tier):
        dest_str = f" for **{slots.destination}**" if slots.destination else ""
        dur_str = f" for a **{slots.duration_days}-day** trip" if slots.duration_days else ""
        msg = (
            f"Got it! **What is your target budget{dur_str}{dest_str}?**\n\n"
            "Please select your preferred spending cap below (we guarantee your final itinerary stays strictly within this amount):"
        )
        opts = [
            "💰 ₹30,000 (Boutique Budget)",
            "✨ ₹50,000 (Curated Comfort)",
            "👑 ₹1,00,000+ (Luxury Heritage)"
        ]
        return {
            "assistant_response": msg,
            "clarification_options": opts,
            "messages": state.messages + [{"role": "assistant", "content": msg}]
        }

    # 5. Missing Pace or Vibe (if not mentioned in prompt)
    if not (slots.pace or slots.vibe_preference):
        msg = f"Almost there! **What travel pace do you prefer for this {slots.duration_days}-day journey to {slots.destination}?**"
        opts = [
            "🌸 Leisure Pace (Slow & Relaxed)",
            "⚖️ Balanced Pace (Curated Highlights)",
            "🥾 Explorer Pace (Active Hikes & Studios)"
        ]
        return {
            "assistant_response": msg,
            "clarification_options": opts,
            "messages": state.messages + [{"role": "assistant", "content": msg}]
        }

    # Fallback if anything else is missing
    msg = f"Almost ready to build your plan for **{slots.destination}**! Please choose your preferred style below:"
    opts = ["🌸 Leisure Pace", "⚖️ Balanced Pace", "🥾 Explorer Pace"]
    return {
        "assistant_response": msg,
        "clarification_options": opts,
        "messages": state.messages + [{"role": "assistant", "content": msg}]
    }


def node_compose_itinerary(state: AgentState) -> Dict[str, Any]:
    """Node 3: Compose the grounded itinerary strictly from the curated India dataset."""
    itinerary = compose_grounded_itinerary(state.slots)

    # Clear clarification options once itinerary is ready
    gemini_narrative = call_gemini_for_narrative(state.messages, itinerary)
    if gemini_narrative:
        return {
            "itinerary": itinerary,
            "clarification_options": [],
            "assistant_response": gemini_narrative,
            "messages": state.messages + [{"role": "assistant", "content": gemini_narrative}]
        }

    # Deterministic formatted message fallback
    budget_line = f"💰 **Budget Tier**: {itinerary.budget_tier} | **Estimated Cost**: ₹{itinerary.estimated_total_cost_inr:,} (Strictly within budget)\n" if itinerary.max_budget_inr else ""
    lines = [
        f"### 🌿 Your Personalized {itinerary.total_days}-Day {itinerary.circuit_name}",
        f"*{itinerary.tagline}*\n",
        f"**Traveler Profile**: {itinerary.traveler_profile} | **Pace**: {itinerary.pace}",
        budget_line,
        f"**Why this is curated for you**: {itinerary.why_personalized}\n",
        "#### 🏡 Handpicked Authentic Stays (No Generic Chain Hotels):"
    ]

    for s in itinerary.stays_summary:
        lines.append(f"• **{s['stay_name']}** ({s['hub']}) — *{s['stay_type']}*\n  *{s['why_special']}*\n  💰 {s['price_approx']} | 💡 *Tip: {s['booking_advice']}*")

    lines.append("\n*You are not locked into any single property! Explore candidate hotels with verified pictures, pricing ranges, in-house food availability, breakfast, and Wi-Fi status in the 🏨 Hotel Recommendations tab below.*")

    full_text = "\n".join(lines)
    return {
        "itinerary": itinerary,
        "clarification_options": [],
        "assistant_response": full_text,
        "messages": state.messages + [{"role": "assistant", "content": full_text}]
    }


def create_trip_agent_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("extract_slots", node_extract)
    workflow.add_node("ask_clarification", node_ask_clarification)
    workflow.add_node("compose_itinerary", node_compose_itinerary)

    workflow.add_edge(START, "extract_slots")
    workflow.add_conditional_edges(
        "extract_slots",
        router_decision,
        {
            "ask_clarification": "ask_clarification",
            "compose_itinerary": "compose_itinerary"
        }
    )
    workflow.add_edge("ask_clarification", END)
    workflow.add_edge("compose_itinerary", END)

    return workflow.compile()
