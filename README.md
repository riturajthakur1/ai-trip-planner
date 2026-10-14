# 🌿 Bespoke AI Trip Planning Agent (India Edition)

An intelligent, stateful trip planner built with **Python, LangGraph, Instructor, and Gemini API**, grounded strictly on a **curated, non-generic dataset of India**.

---

## 1. Why this is Different from Generic AI Trip Planners

Most generic trip planners ask an LLM to hallucinate recommendations, resulting in generic outputs like "Taj Hotel", "Marriott", or standard tourist traps. 

Inspired by our reverse-engineering of `takeoff.wwmib.com`, this agent uses a **Catalog-Grounded Architecture**:
1. **Adaptive Slot-Filling**: Rather than a rigid 7-step wizard, it extracts all user parameters dynamically (Destination, Duration, Month, Travelers, Pace, Vibe, Budget).
2. **Deterministic Catalog Grounding**: Stays, activities, dining, and transfer logistics are retrieved from a verified, characterful dataset (e.g., 18th-century Rajput havelis, riverside pine-wood cottages, colonial cardamom plantation bungalows).
3. **No Hallucinations**: Every stay, price estimate, and insider advice is real and verifiable.

---

## 2. Dataset Format Specification

When your team provides your real dataset later, format it as a JSON file matching the schema in `data/schema.py`:

```json
{
  "circuits": [
    {
      "circuit_id": "IN-RAJ-01",
      "circuit_name": "Mewar & Marwar Heritage Trail",
      "region": "Rajasthan",
      "ideal_duration_days": [5, 8],
      "best_months": ["October", "November", "December", "January", "February", "March"],
      "hubs": ["Udaipur", "Jawai", "Jodhpur"],
      "transfer_logistics": {
        "Udaipur_to_Jawai": "Scenic 3-hour private countryside drive via Ranakpur Jain Temple"
      },
      "tagline": "Restored lake havelis, wild granite hills with leopard trackers, and the indigo alleys of Jodhpur."
    }
  ],
  "stays": [
    {
      "id": "stay_001",
      "name": "Amet Haveli",
      "circuit_id": "IN-RAJ-01",
      "destination": "Udaipur",
      "neighborhood": "Hanuman Ghat",
      "price_tier": "premium_charm",
      "approx_price_per_night_inr": 13500,
      "vibe_tags": ["heritage_royal", "slow_coastal"],
      "stay_type": "Restored 18th-century Rajput Haveli",
      "why_special": "Stone arches right on Lake Pichola with tranquil courtyard and unobstructed views of City Palace across the water.",
      "best_for": ["couples", "honeymoon", "architecture-lovers"],
      "highlight_amenities": ["Direct Lakefront Terrace", "Ambrai Dining", "Courtyard Plunge Pool"],
      "booking_advice": "Request lake-facing heritage suite on the upper level for maximum privacy."
    }
  ],
  "activities": [
    {
      "id": "act_001",
      "destination": "Udaipur",
      "circuit_id": "IN-RAJ-01",
      "title": "Private Wooden Boat Ride to Hidden Ghats",
      "time_slot": "sunset",
      "duration_hours": 1.5,
      "pace_suitability": ["leisure", "balanced"],
      "category": "nature_walk",
      "description": "Escape the crowded ferry boats with a slow wooden hand-rowed boat gliding past Gangaur Ghat.",
      "insider_tip": "Ask boatman to steer towards the rear walls of Jagmandir Island for the most serene sunset reflection.",
      "is_offbeat": true
    }
  ],
  "dining": [
    {
      "id": "dine_001",
      "destination": "Udaipur",
      "name": "Ambrai at Amet Haveli",
      "cuisine_type": "Mewari & Mughlai",
      "vibe": "Waterfront candlelit dining facing illuminated City Palace",
      "must_try": "Mewari Laal Maas with Bajra Roti and Ker Sangri",
      "price_for_two_inr": 3200
    }
  ]
}
```

### Supported Enumerations:
* `PaceLevel`: `leisure` (1 activity/day), `balanced` (2 activities/day), `explorer` (3+ activities/day)
* `PriceTier`: `boutique_budget` (₹3.5k–₹7k), `premium_charm` (₹7.5k–₹15k), `luxury_heritage` (₹16k–₹35k+)
* `VibeCategory`: `heritage_royal`, `mountain_serene`, `slow_coastal`, `forest_wildlife`, `offbeat_cultural`, `bohemian_artistic`

---

## 3. Project Directory Structure

```
ai-trip-planner/
├── agent/
│   ├── composer.py          # Grounded itinerary engine & duration balancer
│   ├── extractor.py         # Instructor / Gemini + deterministic slot-filling
│   ├── graph.py             # LangGraph state machine & decision routers
│   └── state.py             # Pydantic state models for conversation & itinerary
├── api/
│   └── server.py            # FastAPI REST & session endpoints
├── data/
│   ├── curated_india_dataset.json  # Curated non-generic India dataset
│   ├── db.py                # Fast in-memory index & query engine
│   └── schema.py            # Pydantic schema for the travel dataset
├── ui/
│   └── app.py               # Modern Streamlit Clean Chat Runner
└── README.md
```

---

## 4. How to Run the Applications

### Option A: Launch the Streamlit Chat Runner (Recommended for Demos)
Run the Streamlit app directly from the project directory:
```bash
cd /Users/rituraj/.gemini/antigravity/scratch/ai-trip-planner
streamlit run ui/app.py
```
This opens the browser at `http://localhost:8501` featuring:
* Real-time slot extraction sidebar (watches destination, travelers, duration, pace update live).
* 1-click preset sample trip scenarios (Rajasthan, Himachal, Kerala).
* Rich stay cards with pricing, descriptions, and insider booking tips.
* Complete day-by-day itineraries.

### Option B: Launch the FastAPI Backend
If you want to consume the agent via API:
```bash
cd /Users/rituraj/.gemini/antigravity/scratch/ai-trip-planner
python3 -m uvicorn api.server:app --reload --port 8000
```
API Documentation will be live at `http://localhost:8000/docs`.

---

## 5. Setting up Gemini API Key (Optional)
The agent includes a deterministic rule-based extractor that works right out of the box. To enable enhanced semantic extraction with Google Gemini:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
