"""
Streamlit Clean Chat Runner for the Curated India Trip Planning AI Agent.
Designed for high legibility, clear contrast, and intuitive client demonstration.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st
from agent.graph import create_trip_agent_graph
from agent.state import AgentState, TravelSlots
from agent.composer import compose_grounded_itinerary
from agent.pdf_generator import build_pdf_itinerary
from data.db import TravelDatabase

st.set_page_config(
    page_title="Curated India AI Trip Planner",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-contrast, theme-safe styling (ensures text is always 100% readable)
st.markdown("""
<style>
    /* Card containers with explicit readable colors */
    .plan-card {
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .plan-card h4 {
        color: #0F172A;
        margin-top: 0;
        margin-bottom: 8px;
    }
    .plan-card p {
        color: #334155;
        font-size: 14px;
        line-height: 1.5;
        margin-bottom: 6px;
    }
    .stay-badge {
        display: inline-block;
        background-color: #E0F2FE;
        color: #0369A1;
        font-size: 12px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        margin-bottom: 8px;
    }
    .price-tag {
        font-weight: 700;
        color: #047857;
    }
    .tip-box {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "graph" not in st.session_state:
    st.session_state.graph = create_trip_agent_graph()

if "agent_state" not in st.session_state or not hasattr(st.session_state.agent_state, "clarification_options"):
    st.session_state.agent_state = AgentState(
        messages=[
            {
                "role": "assistant",
                "content": (
                    "Namaste! 🙏 I am your **Curated India AI Travel Consultant**.\n\n"
                    "Unlike standard search engines that recommend generic business hotels, "
                    "I design personalized journeys grounded in **authentic heritage havelis, riverside pine cottages, "
                    "tea-estate bungalows, and offbeat local experiences**.\n\n"
                    "Tell me, where in India are you thinking of traveling, or what kind of trip are you seeking?"
                )
            }
        ]
    )

db = TravelDatabase.get_instance()
slots: TravelSlots = st.session_state.agent_state.slots
has_itinerary = st.session_state.agent_state.itinerary is not None

# ================= SIDEBAR =================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=600&q=80", width="stretch")
    st.title("🧭 Traveler Profile")
    st.caption("Live AI Slot-Tracker (Extracted automatically from chat)")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Destination", slots.destination or "Not set")
        st.metric("Travelers", slots.traveler_profile or "Not set")
    with col2:
        st.metric("Duration", f"{slots.duration_days} Days" if slots.duration_days else "Not set")
        st.metric("Budget Cap", f"₹{slots.max_budget_inr:,}" if slots.max_budget_inr else "Not set")

    if slots.pace:
        st.caption(f"⚡ **Pace**: {slots.pace.value.capitalize()}")
    if slots.vibe_preference:
        st.info(f"🎨 **Vibe**: {slots.vibe_preference}")

    if has_itinerary:
        st.success("✅ **Status**: Grounded Itinerary Generated")
    else:
        st.warning("⏳ **Status**: Inquiring & Personalizing...")

    api_key_val = os.environ.get("GEMINI_API_KEY", "")
    if api_key_val and api_key_val != "YOUR_GEMINI_API_KEY_HERE":
        st.success("🤖 **Gemini AI**: Connected & Answering")
    else:
        st.info("⚙️ **AI Engine**: Add key in `.env` for Gemini answers")

    st.divider()

    st.subheader("📚 Available India Circuits")
    for circuit in db.dataset.circuits:
        with st.expander(f"📍 {circuit.circuit_name}"):
            st.write(f"*{circuit.tagline}*")
            st.write(f"**Region**: {circuit.region}")
            st.write(f"**Hubs**: {', '.join(circuit.hubs)}")
            st.write(f"**Best Months**: {', '.join(circuit.best_months[:3])}")

    if st.button("🔄 Start New Plan", width="stretch"):
        st.session_state.agent_state = AgentState(
            messages=[
                {
                    "role": "assistant",
                    "content": "Namaste! Where would you like to travel in India?"
                }
            ]
        )
        st.rerun()


# ================= MAIN PAGE =================
st.title("🌿 Bespoke India AI Trip Planner")
st.markdown("Stateful trip planner built with **LangGraph** — strictly grounded in authentic stays, secret trails, and verified local circuits.")

# Quick Starters (Only shown on fresh conversation)
if len(st.session_state.agent_state.messages) <= 1:
    st.markdown("##### ⚡ Quick Example Prompts (Click to test instantly):")
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    row2_c1, row2_c2 = st.columns(2)
    preset_prompt = None

    with row1_c1:
        if st.button("🏔️ 5-Day Himachal Pine Cottages", width="stretch"):
            preset_prompt = "I want a 5-day relaxing mountain getaway for a couple in Himachal Pradesh with riverside wooden cottages."
    with row1_c2:
        if st.button("🏰 6-Day Rajasthan Luxury Havelis", width="stretch"):
            preset_prompt = "Looking for a 6-day heritage anniversary trip for a couple in Rajasthan, staying at lakeside havelis with a slow leisure pace."
    with row1_c3:
        if st.button("🌴 6-Day Kerala Slow Living", width="stretch"):
            preset_prompt = "Plan a 6-day slow coastal and tea plantation journey for 2 in Kerala with private plantation trails."
    with row2_c1:
        if st.button("🛶 5-Day Kashmir Cedar Houseboats", width="stretch"):
            preset_prompt = "Plan a 5-day romantic trip to Kashmir for a couple staying on Nigeen Lake houseboats and Lidder pine chalets, leisure pace."
    with row2_c2:
        if st.button("🏛️ 4-Day Mumbai Art Deco & Alibaug", width="stretch"):
            preset_prompt = "Plan a trip for Mumbai and Alibaug."

    if preset_prompt:
        st.session_state.agent_state.messages.append({"role": "user", "content": preset_prompt})
        with st.spinner("Analyzing travel preferences and matching catalog..."):
            result = st.session_state.graph.invoke(st.session_state.agent_state)
            st.session_state.agent_state = AgentState(**result)
            st.rerun()

# Display Chat Conversation
st.markdown("### 💬 Conversation")
messages = st.session_state.agent_state.messages
for i, msg in enumerate(messages):
    is_last = (i == len(messages) - 1)
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown(msg["content"])
            # If this is the latest assistant message asking clarification, show clickable option buttons!
            clarify_opts = getattr(st.session_state.agent_state, "clarification_options", [])
            is_ready = getattr(st.session_state.agent_state, "ready_for_itinerary", False)
            if is_last and clarify_opts and not is_ready:
                st.markdown("<p style='font-size: 13px; color: #334155; font-weight: 600; margin-top: 12px; margin-bottom: 6px;'>👇 Tap an option below to reply without typing:</p>", unsafe_allow_html=True)
                opt_cols = st.columns(min(len(clarify_opts), 4))
                for idx, opt in enumerate(clarify_opts):
                    col_idx = idx % len(opt_cols)
                    with opt_cols[col_idx]:
                        if st.button(opt, key=f"clarify_btn_{i}_{idx}", width="stretch"):
                            st.session_state.agent_state.messages.append({"role": "user", "content": opt})
                            with st.spinner("Updating preferences..."):
                                result = st.session_state.graph.invoke(st.session_state.agent_state)
                                st.session_state.agent_state = AgentState(**result)
                                st.rerun()

# Render Structured Visual Itinerary Dashboard if available
itinerary = st.session_state.agent_state.itinerary
if itinerary:
    st.divider()
    st.header(f"🗺️ {itinerary.circuit_name} ({itinerary.total_days} Days)")
    st.caption(f"_{itinerary.tagline}_")

    if itinerary.max_budget_inr:
        surplus = itinerary.max_budget_inr - itinerary.estimated_total_cost_inr
        st.markdown(
            f"""
            <div style="background-color: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; color: #14532D;">
                <div style="font-weight: 700; font-size: 16px; margin-bottom: 4px;">
                    ✅ Budget Guarantee: Total Package Strictly Within ₹{itinerary.max_budget_inr:,}
                </div>
                <div style="font-size: 14px; color: #166534;">
                    Estimated Total: <strong>₹{itinerary.estimated_total_cost_inr:,}</strong> &nbsp;•&nbsp; 
                    Safe Margin: <strong>₹{surplus:,}</strong> &nbsp;•&nbsp;
                    Stays: <strong>₹{itinerary.cost_breakdown.get('Handpicked Stays', 0):,}</strong> &nbsp;•&nbsp; 
                    Dining: <strong>₹{itinerary.cost_breakdown.get('Authentic Regional Dining', 0):,}</strong> &nbsp;•&nbsp; 
                    Experiences: <strong>₹{itinerary.cost_breakdown.get('Local Experiences & Entries', 0):,}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    tab1, tab2, tab3, tab4 = st.tabs(["📅 Day-by-Day Flow", "🏨 Hotel Recommendations (Pictures & Choices)", "🚗 Route & Logistics", "💰 Financial Breakdown"])

    with tab1:
        for d in itinerary.days:
            with st.expander(f"📍 Day {d.day_number}: {d.destination} — {d.theme}", expanded=(d.day_number == 1)):
                st.markdown(f"**🏡 Stay:** `{d.stay_name}`")
                st.markdown(f"**🌅 Morning:** {d.morning_activity}")
                if d.afternoon_activity:
                    st.markdown(f"**☀️ Afternoon:** {d.afternoon_activity}")
                if d.sunset_evening_activity:
                    st.markdown(f"**🌇 {d.sunset_evening_activity}**")
                if d.dining_highlight:
                    st.markdown(f"**🍽️ Dining:** {d.dining_highlight}")
                st.markdown(f"<div class='tip-box'>💡 <strong>Insider Advice:</strong> {d.insider_advice}</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("### 🏨 Handpicked Hotel Recommendations (Explore & Choose)")
        st.caption("We don't lock you into a single hotel. Explore our curated candidate properties below with real photos, pricing ranges, in-house food, breakfast, and Wi-Fi details. Tap 'Select for [Hub]' to swap your property anytime:")

        rec_by_hub = itinerary.recommended_hotels_by_hub or {}
        if not rec_by_hub:
            rec_by_hub = {s.get("hub", "Destination"): [s] for s in itinerary.stays_summary}

        for hub, hotels in rec_by_hub.items():
            st.markdown(f"#### 📍 Curated Hotel Options in **{hub}**")
            cols = st.columns(min(len(hotels), 3))
            current_selected_id = (itinerary.selected_stay_ids or {}).get(hub)

            for idx, hotel in enumerate(hotels):
                with cols[idx % len(cols)]:
                    img_url = hotel.get("image_url") or "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
                    st.image(img_url, use_container_width=True)

                    is_active = (hotel.get("id") == current_selected_id) or (hotel.get("name") in [s["stay_name"] for s in itinerary.stays_summary if s.get("hub") == hub])

                    st.markdown(f"**{hotel['name']}**")
                    st.caption(f"_{hotel.get('stay_type', '')} • {hotel.get('neighborhood', hub)}_")
                    st.markdown(f"**💰 Pricing Range:** `{hotel.get('price_range', hotel.get('price_approx', ''))}`")

                    # Food Available
                    if hotel.get("food_available", True):
                        st.markdown(f"🍽️ **Food Available:** ✅ Yes — *{hotel.get('food_details', 'In-house dining')}*")
                    else:
                        st.markdown(f"🍽️ **Food Available:** ❌ No — *{hotel.get('food_details', 'Nearby cafes only')}*")

                    # Breakfast Available
                    if hotel.get("breakfast_available", True):
                        st.markdown(f"☕ **Breakfast:** ✅ Included — *{hotel.get('breakfast_details', 'Artisanal breakfast')}*")
                    else:
                        st.markdown(f"☕ **Breakfast:** ❌ Not Included — *{hotel.get('breakfast_details', 'Available on request')}*")

                    # Wi-Fi Available
                    if hotel.get("wifi_available", True):
                        st.markdown(f"📶 **Wi-Fi:** ✅ Yes — *{hotel.get('wifi_details', 'High-speed Wi-Fi')}*")
                    else:
                        st.markdown(f"📶 **Wi-Fi:** ❌ No — *{hotel.get('wifi_details', 'Digital detox')}*")

                    st.markdown(f"<div class='plan-card' style='margin-top: 6px; padding: 10px;'><p style='font-size: 13px; margin: 0;'>{hotel.get('why_special', '')}</p><div class='tip-box' style='margin-top: 6px; font-size: 12px;'>💡 <strong>Booking Tip:</strong> {hotel.get('booking_advice', '')}</div></div>", unsafe_allow_html=True)

                    if is_active:
                        st.success("✅ **Active in Itinerary**")
                    else:
                        btn_key = f"pick_stay_{hub}_{hotel.get('id', idx)}"
                        if st.button(f"🔘 Select for {hub}", key=btn_key, width="stretch"):
                            existing_overrides = dict(st.session_state.agent_state.itinerary.selected_stay_ids or {})
                            existing_overrides[hub] = hotel["id"]
                            new_itinerary = compose_grounded_itinerary(st.session_state.agent_state.slots, selected_stay_override=existing_overrides)
                            st.session_state.agent_state.itinerary = new_itinerary
                            st.rerun()
            st.divider()

    with tab3:
        circuit_data = db.circuits_by_id.get(st.session_state.agent_state.circuit_id)
        if circuit_data:
            st.markdown(f"**Region:** {circuit_data.region}")
            st.markdown(f"**Hubs Included:** {' ➔ '.join(circuit_data.hubs)}")
            st.markdown(f"**Best Months to Visit:** {', '.join(circuit_data.best_months)}")
            st.markdown("**Transfer Logistics:**")
            for route_name, desc in circuit_data.transfer_logistics.items():
                st.markdown(f"• **{route_name.replace('_', ' ')}**: {desc}")

    with tab4:
        st.markdown("### 💰 Trip Financial Breakdown")
        st.caption("Detailed estimate for 2 travelers grounded strictly in verified catalog prices")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            st.metric("Target Budget Cap", f"₹{itinerary.max_budget_inr:,}" if itinerary.max_budget_inr else "Not set")
        with f_col2:
            st.metric("Estimated Package Cost", f"₹{itinerary.estimated_total_cost_inr:,}")
        with f_col3:
            if itinerary.max_budget_inr:
                margin = itinerary.max_budget_inr - itinerary.estimated_total_cost_inr
                st.metric("Budget Cushion", f"₹{margin:,}", delta="Safe & within limit")
            else:
                st.metric("Tier", itinerary.budget_tier)

        st.markdown("#### Itemized Category Allocations:")
        for cat, amt in itinerary.cost_breakdown.items():
            st.markdown(f"• **{cat}**: `₹{amt:,}`")

    # One-click Refinement Toolbar
    st.markdown("#### ⚡ Refine this Itinerary:")
    ref_c1, ref_c2, ref_c3, ref_c4 = st.columns(4)
    refine_action = None
    with ref_c1:
        if st.button("🌸 Leisure / Slower Pace", width="stretch"):
            refine_action = "Make the pace more leisurely with slower mornings and unhurried meals."
    with ref_c2:
        if st.button("🥾 Active / Explorer Pace", width="stretch"):
            refine_action = "Make the pace active with more nature hikes, walks, and artisan studios."
    with ref_c3:
        if st.button("💰 Boutique Budget Stays", width="stretch"):
            refine_action = "Switch stays to characterful boutique budget homestays."
    with ref_c4:
        if st.button("👑 Luxury Heritage Stays", width="stretch"):
            refine_action = "Upgrade stays to luxury royal heritage properties with private views."

    if refine_action:
        st.session_state.agent_state.messages.append({"role": "user", "content": refine_action})
        with st.spinner("Refining your itinerary..."):
            result = st.session_state.graph.invoke(st.session_state.agent_state)
            st.session_state.agent_state = AgentState(**result)
            st.rerun()

    # Download Itinerary (PDF as primary for normal users, Markdown as secondary)
    st.markdown("#### 📄 Save & Share Your Itinerary:")
    try:
        pdf_bytes = build_pdf_itinerary(itinerary, st.session_state.agent_state.circuit_id)
        clean_cname = itinerary.circuit_name.lower().replace(' ', '_').replace('&', 'and')
        pdf_filename = f"{clean_cname}_{itinerary.total_days}days_itinerary.pdf"
    except Exception as e:
        pdf_bytes = None
        pdf_filename = "itinerary.pdf"

    down_c1, down_c2 = st.columns([3, 1])
    with down_c1:
        if pdf_bytes:
            st.download_button(
                label="📄 Download Ready-to-Print Itinerary (PDF)",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                width="stretch",
                type="primary"
            )
        else:
            st.warning("Could not pre-render PDF.")
    with down_c2:
        st.download_button(
            label="📝 Raw Markdown",
            data=st.session_state.agent_state.messages[-1]["content"],
            file_name=f"{itinerary.circuit_name.lower().replace(' ', '_')}_{itinerary.total_days}days.md",
            mime="text/markdown",
            width="stretch"
        )

# ================= CHAT INPUT =================
user_prompt = st.chat_input("Type your travel request (e.g. 'Couple, 5 days in Himachal, relaxed pace')...")
if user_prompt:
    st.session_state.agent_state.messages.append({"role": "user", "content": user_prompt})
    with st.spinner("Thinking and consulting curated catalog..."):
        result = st.session_state.graph.invoke(st.session_state.agent_state)
        st.session_state.agent_state = AgentState(**result)
        st.rerun()
