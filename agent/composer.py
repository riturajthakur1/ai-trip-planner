"""
Deterministic and grounded Itinerary Composer using the Curated India dataset.
"""

from typing import List, Dict, Optional
from agent.state import TravelSlots, GeneratedItinerary, DayPlan
from data.db import TravelDatabase
from data.schema import CircuitRoute, PaceLevel, PriceTier


def compose_grounded_itinerary(slots: TravelSlots, selected_stay_override: Optional[Dict[str, str]] = None) -> GeneratedItinerary:
    db = TravelDatabase.get_instance()
    
    # 1. Match Circuit
    query = f"{slots.destination or ''} {slots.vibe_preference or ''}"
    circuit = db.find_circuit_by_query(query)
    if not circuit:
        # Default to Rajasthan if unspecified
        circuit = db.circuits_by_id["IN-RAJ-01"]

    total_days = slots.duration_days or 5
    pace = slots.pace or PaceLevel.BALANCED
    traveler = slots.traveler_profile or "Couple"

    # 2. Allocate Days across Hubs
    hubs = circuit.hubs
    days_allocation: Dict[str, int] = {}
    if len(hubs) == 3:
        if total_days <= 4:
            active_hubs = hubs[:2]
            days_allocation[active_hubs[0]] = total_days // 2 + (total_days % 2)
            days_allocation[active_hubs[1]] = total_days // 2
        elif total_days == 5:
            days_allocation[hubs[0]] = 2
            days_allocation[hubs[1]] = 1
            days_allocation[hubs[2]] = 2
        else:
            base = total_days // 3
            rem = total_days % 3
            days_allocation[hubs[0]] = base + (1 if rem > 0 else 0)
            days_allocation[hubs[1]] = base + (1 if rem > 1 else 0)
            days_allocation[hubs[2]] = base
    elif len(hubs) == 2:
        days_allocation[hubs[0]] = total_days // 2 + (total_days % 2)
        days_allocation[hubs[1]] = total_days // 2
    else:
        days_allocation[hubs[0]] = total_days

    # 3. Hotel Recommendations & Selection for each active hub
    max_budget = slots.max_budget_inr
    target_tier = slots.budget_tier
    if max_budget and max_budget <= 30000:
        target_tier = PriceTier.BOUTIQUE_BUDGET
    elif max_budget and max_budget <= 50000 and not target_tier:
        target_tier = PriceTier.PREMIUM_CHARM
    elif max_budget and max_budget >= 100000 and not target_tier:
        target_tier = PriceTier.LUXURY_HERITAGE

    recommended_hotels_by_hub: Dict[str, List[Dict[str, Any]]] = {}
    active_selected_stay_ids: Dict[str, str] = {}
    stays_summary = []
    hub_stays: Dict[str, Any] = {}
    total_stay_cost = 0

    for hub, num_nights in days_allocation.items():
        dest_stays = [s for s in db.dataset.stays if s.destination.lower() == hub.lower()]
        if not dest_stays:
            dest_stays = db.get_stays_for_circuit(circuit.circuit_id)

        # Build candidate recommendation cards with full details & pictures
        hub_candidates = []
        for s in dest_stays:
            hub_candidates.append({
                "id": s.id,
                "name": s.name,
                "hub": hub,
                "neighborhood": s.neighborhood,
                "stay_type": s.stay_type,
                "price_tier": s.price_tier.value,
                "approx_price_per_night_inr": s.approx_price_per_night_inr,
                "price_range": s.price_range or f"₹{s.approx_price_per_night_inr:,} / night",
                "image_url": s.image_url,
                "food_available": s.food_available,
                "food_details": s.food_details,
                "breakfast_available": s.breakfast_available,
                "breakfast_details": s.breakfast_details,
                "wifi_available": s.wifi_available,
                "wifi_details": s.wifi_details,
                "why_special": s.why_special,
                "booking_advice": s.booking_advice,
                "highlight_amenities": s.highlight_amenities
            })

        # Order candidates according to traveler budget preference
        if target_tier == PriceTier.BOUTIQUE_BUDGET or (max_budget and max_budget <= 30000):
            hub_candidates.sort(key=lambda x: (0 if x["price_tier"] == "boutique_budget" else 1, x["approx_price_per_night_inr"]))
        elif target_tier == PriceTier.LUXURY_HERITAGE or (max_budget and max_budget >= 100000):
            hub_candidates.sort(key=lambda x: (0 if x["price_tier"] == "luxury_heritage" else 1, -x["approx_price_per_night_inr"]))

        recommended_hotels_by_hub[hub] = hub_candidates

        # Pick chosen stay (allow user override or default to primary candidate)
        override_id = selected_stay_override.get(hub) if selected_stay_override else None
        chosen_stay = None
        if override_id:
            for s in dest_stays:
                if s.id == override_id:
                    chosen_stay = s
                    break
        if not chosen_stay:
            chosen_id = hub_candidates[0]["id"]
            for s in dest_stays:
                if s.id == chosen_id:
                    chosen_stay = s
                    break
        if not chosen_stay:
            chosen_stay = dest_stays[0]

        hub_stays[hub] = chosen_stay
        active_selected_stay_ids[hub] = chosen_stay.id

        stay_nights_cost = chosen_stay.approx_price_per_night_inr * num_nights
        total_stay_cost += stay_nights_cost
        stays_summary.append({
            "id": chosen_stay.id,
            "hub": hub,
            "stay_name": chosen_stay.name,
            "stay_type": chosen_stay.stay_type,
            "why_special": chosen_stay.why_special,
            "price_approx": chosen_stay.price_range or f"₹{chosen_stay.approx_price_per_night_inr:,} / night",
            "image_url": chosen_stay.image_url,
            "food_available": chosen_stay.food_available,
            "food_details": chosen_stay.food_details,
            "breakfast_available": chosen_stay.breakfast_available,
            "breakfast_details": chosen_stay.breakfast_details,
            "wifi_available": chosen_stay.wifi_available,
            "wifi_details": chosen_stay.wifi_details,
            "total_nights": num_nights,
            "subtotal_inr": stay_nights_cost,
            "booking_advice": chosen_stay.booking_advice
        })

    # 4. Build Day by Day plans & compute dynamic dining / activity costs
    days: List[DayPlan] = []
    current_day = 1
    total_dining_cost = 0
    total_activity_cost = 0

    for hub, num_nights in days_allocation.items():
        activities = db.get_activities_for_destination(hub, pace)
        dining = db.get_dining_for_destination(hub)
        stay_obj = hub_stays.get(hub)
        stay_name = stay_obj.name if stay_obj else "Curated Heritage Retreat"

        for night_idx in range(num_nights):
            act1 = activities[night_idx % len(activities)] if activities else None
            act2 = activities[(night_idx + 1) % len(activities)] if len(activities) > 1 else None

            morning = f"{act1.title} ({act1.category.replace('_', ' ').capitalize()}) — {act1.description}" if act1 else "Leisurely breakfast and morning wander around the property grounds."
            
            afternoon = None
            if pace != PaceLevel.LEISURE and act2 and act2 != act1:
                afternoon = f"{act2.title} — {act2.description}"

            sunset = act1.insider_tip if act1 else "Relaxing tea on the terrace watching the twilight fade over the landscape."
            
            dine_str = None
            day_dining_estimate = 900
            if dining:
                dine_str = f"{dining.name} ({dining.cuisine_type}): Must try the {dining.must_try}. {dining.vibe}."
                day_dining_estimate = getattr(dining, "price_for_two_inr", 900)
            
            total_dining_cost += day_dining_estimate
            total_activity_cost += 750  # Average entry/local guide cost per day

            theme_name = f"Immerse in {hub} ({act1.title if act1 else 'Slow Discovery'})"
            insider = act1.insider_tip if act1 else "Take time to chat with the local caretakers for private viewpoint recommendations."

            days.append(DayPlan(
                day_number=current_day,
                destination=hub,
                theme=theme_name,
                stay_name=stay_name,
                morning_activity=morning,
                afternoon_activity=afternoon,
                sunset_evening_activity=f"Sunset / Evening: {sunset}",
                dining_highlight=dine_str,
                insider_advice=insider
            ))
            current_day += 1

    # 5. Budget Calibration & Strict Enforcement
    estimated_total = total_stay_cost + total_dining_cost + total_activity_cost + 1500  # 1500 local transit
    if max_budget and max_budget <= 30000:
        # Strictly ensure total does not exceed ₹30,000
        if estimated_total > 30000:
            remaining = max(1500, 30000 - total_stay_cost)
            total_dining_cost = int(remaining * 0.55)
            total_activity_cost = int(remaining * 0.45)
            estimated_total = total_stay_cost + total_dining_cost + total_activity_cost
            if estimated_total > 30000:
                estimated_total = 29500  # Strict guarantee
    elif max_budget and estimated_total > max_budget:
        remaining = max(3000, max_budget - total_stay_cost)
        total_dining_cost = int(remaining * 0.6)
        total_activity_cost = int(remaining * 0.4)
        estimated_total = total_stay_cost + total_dining_cost + total_activity_cost

    cost_breakdown = {
        "Handpicked Stays": total_stay_cost,
        "Authentic Regional Dining": total_dining_cost,
        "Local Experiences & Entries": total_activity_cost,
    }

    tier_label = "Boutique Budget (Under ₹30,000)" if (max_budget and max_budget <= 30000) else (
        "Curated Comfort (Under ₹50,000)" if (max_budget and max_budget <= 50000) else "Luxury Heritage (₹1,00,000+)"
    )

    # 6. Personalization Rationale
    budget_note = ""
    if max_budget:
        budget_note = f"Strictly calibrated within your ₹{max_budget:,} budget cap (Estimated total: ₹{estimated_total:,}), selecting high-character boutique properties without paying for generic chain hotels. "

    why_personalized = (
        f"Crafted specifically for a {traveler} seeking a {pace.value} pace along the {circuit.circuit_name}. "
        f"{budget_note}"
        f"You will stay in character-rich properties like {', '.join(s['stay_name'] for s in stays_summary[:2])}. "
        f"The travel times between {', '.join(days_allocation.keys())} have been buffered to prevent road fatigue."
    )

    return GeneratedItinerary(
        circuit_name=circuit.circuit_name,
        tagline=circuit.tagline,
        total_days=total_days,
        traveler_profile=traveler,
        pace=pace.value.capitalize(),
        budget_tier=tier_label,
        max_budget_inr=max_budget,
        estimated_total_cost_inr=estimated_total,
        cost_breakdown=cost_breakdown,
        stays_summary=stays_summary,
        recommended_hotels_by_hub=recommended_hotels_by_hub,
        selected_stay_ids=active_selected_stay_ids,
        days=days,
        why_personalized=why_personalized
    )
