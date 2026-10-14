"""
Database and retrieval helper for the Curated India Trip Planner dataset.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from data.schema import (
    CuratedIndiaDataset,
    CircuitRoute,
    CuratedStay,
    CuratedActivity,
    DiningSpot,
    PaceLevel,
    PriceTier,
    VibeCategory
)

DATA_PATH = Path(__file__).parent / "curated_india_dataset.json"


class TravelDatabase:
    _instance = None

    def __init__(self, file_path: Path = DATA_PATH):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        self.dataset = CuratedIndiaDataset(**raw_data)
        self._build_indexes()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _build_indexes(self):
        self.circuits_by_id: Dict[str, CircuitRoute] = {c.circuit_id: c for c in self.dataset.circuits}
        self.stays_by_destination: Dict[str, List[CuratedStay]] = {}
        for stay in self.dataset.stays:
            self.stays_by_destination.setdefault(stay.destination.lower(), []).append(stay)

        self.activities_by_destination: Dict[str, List[CuratedActivity]] = {}
        for act in self.dataset.activities:
            self.activities_by_destination.setdefault(act.destination.lower(), []).append(act)

        self.dining_by_destination: Dict[str, List[DiningSpot]] = {}
        for dine in self.dataset.dining:
            self.dining_by_destination.setdefault(dine.destination.lower(), []).append(dine)

    def find_circuit_by_query(self, query: str) -> Optional[CircuitRoute]:
        """Match query against circuit name, region, hubs, or taglines."""
        q = query.lower()
        for circuit in self.dataset.circuits:
            if circuit.region.lower() in q or circuit.circuit_name.lower() in q:
                return circuit
            for hub in circuit.hubs:
                if hub.lower() in q:
                    return circuit
        # Keyword checks
        if any(w in q for w in ["rajasthan", "mewar", "marwar", "udaipur", "jodhpur", "desert", "haveli"]):
            return self.circuits_by_id.get("IN-RAJ-01")
        if any(w in q for w in ["kerala", "backwaters", "kochi", "munnar", "tea", "marari"]):
            return self.circuits_by_id.get("IN-KER-01")
        if any(w in q for w in ["himachal", "tirthan", "jibhi", "kullu", "manali", "mountain", "himalaya"]):
            return self.circuits_by_id.get("IN-HIM-01")
        if any(w in q for w in ["goa", "fontainhas", "latin", "panjim", "aldona"]):
            return self.circuits_by_id.get("IN-GOA-01")
        if any(w in q for w in ["meghalaya", "shillong", "cherrapunjee", "living roots", "waterfall"]):
            return self.circuits_by_id.get("IN-MEG-01")
        if any(w in q for w in ["kashmir", "srinagar", "pahalgam", "gulmarg", "dal lake", "nigeen", "houseboat"]):
            return self.circuits_by_id.get("IN-KAS-01")
        if any(w in q for w in ["ladakh", "leh", "nubra", "pangong", "monastery", "monasteries", "hunder"]):
            return self.circuits_by_id.get("IN-LAD-01")
        if any(w in q for w in ["mumbai", "bombay", "alibaug", "maharashtra", "colaba", "art deco"]):
            return self.circuits_by_id.get("IN-BOM-01")
        return None

    def get_stays_for_circuit(
        self,
        circuit_id: str,
        price_tier: Optional[PriceTier] = None,
        vibe_preference: Optional[str] = None
    ) -> List[CuratedStay]:
        stays = [s for s in self.dataset.stays if s.circuit_id == circuit_id]
        if price_tier:
            filtered = [s for s in stays if s.price_tier == price_tier]
            if filtered:
                return filtered
        if vibe_preference:
            v_lower = vibe_preference.lower()
            matching = [s for s in stays if any(v_lower in v.value for v in s.vibe_tags)]
            if matching:
                return matching
        return stays

    def get_activities_for_destination(
        self,
        destination: str,
        pace: PaceLevel = PaceLevel.BALANCED
    ) -> List[CuratedActivity]:
        dest_acts = self.activities_by_destination.get(destination.lower(), [])
        if not dest_acts:
            # Fallback search partial
            for k, v in self.activities_by_destination.items():
                if k in destination.lower() or destination.lower() in k:
                    dest_acts = v
                    break
        # Filter by pace if possible, or return all
        pace_matched = [a for a in dest_acts if pace in a.pace_suitability]
        return pace_matched if pace_matched else dest_acts

    def get_dining_for_destination(self, destination: str) -> Optional[DiningSpot]:
        spots = self.dining_by_destination.get(destination.lower(), [])
        if not spots:
            for k, v in self.dining_by_destination.items():
                if k in destination.lower() or destination.lower() in k:
                    spots = v
                    break
        return spots[0] if spots else None
