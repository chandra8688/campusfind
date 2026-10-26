"""
CampusFind - Simple, minimal multilingual lost-and-found matching for college campuses.
Powered by Sarvam AI (Sarvam-105B) and Streamlit.
"""

import os
from datetime import date
from typing import Dict, Any, List
import streamlit as st

from src.config import CAMPUS_LOCATIONS, COMMON_CATEGORIES, get_sarvam_api_key, SARVAM_MODEL_NAME
from src.sarvam_client import extract_attributes_with_sarvam
from src.matcher import compute_match_score, find_matches_for_item, find_all_campus_matches
from src.storage import load_reports, add_report, reset_to_samples, delete_report

# Page configuration
st.set_page_config(
    page_title="CampusFind — Lost & Found",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean, minimal design CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }
    
    /* Clean background */
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Compact Header */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0 16px 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 20px;
    }
    .app-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: #64748B;
        margin: 2px 0 0 0;
    }
    
    /* Minimal status badges */
    .badge-live {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .badge-demo {
        background-color: #F8FAFC;
        color: #475569;
        border: 1px solid #CBD5E1;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    
    /* Compact Match Card */
    .match-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .match-card:hover {
        border-color: #CBD5E1;
    }
    
    .score-badge {
        font-size: 0.9rem;
        font-weight: 700;
        color: #1D4ED8;
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        padding: 4px 10px;
        border-radius: 6px;
    }
    
    .item-pill-lost {
        font-size: 0.72rem;
        font-weight: 600;
        color: #991B1B;
        background: #FEE2E2;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    
    .item-pill-found {
        font-size: 0.72rem;
        font-weight: 600;
        color: #065F46;
        background: #D1FAE5;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    
    .tag-chip {
        display: inline-block;
        background: #F1F5F9;
        color: #334155;
        font-size: 0.75rem;
        font-weight: 500;
        padding: 2px 7px;
        border-radius: 4px;
        margin-right: 4px;
        margin-top: 3px;
    }
    
    /* Form cleanups */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "api_key_override" not in st.session_state:
        st.session_state.api_key_override = ""
    if "quick_fill_lost" not in st.session_state:
        st.session_state.quick_fill_lost = None


init_session_state()

# Determine effective API Key
env_key = get_sarvam_api_key()
active_api_key = env_key or st.session_state.api_key_override.strip()
is_live_key_configured = bool(active_api_key)

# ----------------- SIDEBAR: MINIMAL CONTROLS -----------------
with st.sidebar:
    st.markdown("#### Settings & Data")
    
    # API Key Input
    with st.expander("Sarvam AI Configuration", expanded=not is_live_key_configured):
        input_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.api_key_override,
            placeholder="Paste SARVAM_API_KEY",
            help="Reads SARVAM_API_KEY env variable or session input."
        )
        if input_key != st.session_state.api_key_override:
            st.session_state.api_key_override = input_key
            st.rerun()

    st.markdown("#### Sample Demo Data")
    if st.button("Reload Sample Reports", use_container_width=True):
        reset_to_samples()
        st.success("Sample reports reloaded.")
        st.rerun()
        
    st.caption("Quick sample autofill for 'Report Lost':")
    if st.button("Hinglish: Water Bottle", use_container_width=True):
        st.session_state.quick_fill_lost = {
            "title": "Lost Milton Bottle",
            "desc": "Mera navy blue Milton water bottle library ke 2nd floor pe chhut gaya, uspe Spider-Man sticker hai.",
            "loc": "Central Library (1st/2nd Floor Reading Hall)"
        }
        st.rerun()
    if st.button("Hindi: Casio Calculator", use_container_width=True):
        st.session_state.quick_fill_lost = {
            "title": "Lost Casio Calculator",
            "desc": "मैकेनिकल ब्लॉक रूम 102 में मेरा ब्लैक केसियो कैलकुलेटर छूट गया। रोल नंबर स्टिकर लगा है।",
            "loc": "Mechanical & Civil Engineering Block"
        }
        st.rerun()

    st.divider()
    st.caption("Student contact details are masked. Potential matches are unconfirmed until physical verification.")


# ----------------- COMPACT APP HEADER -----------------
status_badge = (
    '<span class="badge-live">● Sarvam-105B Live</span>'
    if is_live_key_configured
    else '<span class="badge-demo">Sample-Demo Mode (Offline)</span>'
)

st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">CampusFind</div>
        <div class="app-subtitle">Find your lost belongings, faster.</div>
    </div>
    <div>
        {status_badge}
    </div>
</div>
""", unsafe_allow_html=True)


# ----------------- SIMPLE 4-SECTION NAVIGATION -----------------
tab_match, tab_lost, tab_found, tab_inventory = st.tabs([
    "Find Matches",
    "Report Lost",
    "Report Found",
    "Inventory"
])


# ==============================================================================
# SECTION 1: FIND MATCHES (MAIN FOCUS)
# ==============================================================================
with tab_match:
    reports = load_reports()
    
    # Simple search & filter bar
    col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
    with col_s1:
        search_query = st.text_input(
            "Search matches",
            placeholder="Search by keyword, item name, or location...",
            label_visibility="collapsed"
        )
    with col_s2:
        min_threshold = st.slider("Min score (%)", min_value=30, max_value=90, value=40, step=5, label_visibility="collapsed")
    with col_s3:
        btn_find = st.button("Find Matches", type="primary", use_container_width=True)

    matches = find_all_campus_matches(reports, min_score=min_threshold)
    
    if search_query.strip():
        q = search_query.strip().lower()
        matches = [
            m for m in matches
            if q in m["lost"]["title"].lower() or q in m["found"]["title"].lower()
            or q in m["lost"]["raw_description"].lower() or q in m["found"]["raw_description"].lower()
            or q in str(m["lost"]["attributes"]).lower() or q in str(m["found"]["attributes"]).lower()
        ]

    st.markdown(f"<div style='font-size: 0.88rem; color: #64748B; margin: 10px 0 16px 0;'>Showing <b>{len(matches)}</b> potential matches (threshold ≥ {min_threshold}%)</div>", unsafe_allow_html=True)
    
    if not matches:
        st.info("No matches found matching your criteria. Try adjusting the score threshold or search query.")
    else:
        for idx, match in enumerate(matches):
            res = match["match_result"]
            lost = match["lost"]
            found = match["found"]
            score = res["score"]
            conf_label = res["confidence_label"]
            l_attr = lost.get("attributes", {})
            f_attr = found.get("attributes", {})
            
            with st.container():
                st.markdown(f"""
                <div class="match-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span class="score-badge">{score}% Match</span>
                            <span style="font-size: 0.85rem; color: #475569; margin-left: 8px;">{conf_label}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94A3B8;">
                            {lost.get('id')} ⟷ {found.get('id')}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 10px;">
                        <div>
                            <div><span class="item-pill-lost">Lost</span> <b>{lost.get('title')}</b></div>
                            <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">{lost.get('raw_description')}</div>
                            <div style="margin-top: 6px;">
                                <span class="tag-chip">{l_attr.get('item_type')}</span>
                                <span class="tag-chip">{l_attr.get('color')}</span>
                                <span class="tag-chip">{l_attr.get('location')}</span>
                            </div>
                        </div>
                        <div>
                            <div><span class="item-pill-found">Found</span> <b>{found.get('title')}</b></div>
                            <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">{found.get('raw_description')}</div>
                            <div style="margin-top: 6px;">
                                <span class="tag-chip">{f_attr.get('item_type')}</span>
                                <span class="tag-chip">{f_attr.get('color')}</span>
                                <span class="tag-chip">{f_attr.get('location')}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Small scoring breakdown expander
                with st.expander(f"Why this match? ({score}/100)", expanded=False):
                    for factor in res["breakdown"]:
                        pts = factor["points"]
                        pts_str = f"+{pts}" if pts > 0 else f"{pts}"
                        st.write(f"• **{factor['factor']}** ({pts_str}/{factor['max_points']} pts): {factor['detail']}")
                    st.caption("Potential match suggestion based on extracted attributes. Verify physical proof before handover.")
                    
                    # Handover contact details
                    c_l = lost.get("contact", {})
                    c_f = found.get("contact", {})
                    st.write(f"**Contact**: Owner: `{c_l.get('email', 'masked')}` | Finder: `{c_f.get('email', 'masked')}`")


# ==============================================================================
# SECTION 2: REPORT LOST
# ==============================================================================
with tab_lost:
    st.markdown("#### Report a Lost Item")
    st.caption("Submit details in English, Hindi, Hinglish, Tamil, or Telugu. Attributes are extracted automatically.")
    
    qf = st.session_state.quick_fill_lost or {}
    default_title = qf.get("title", "")
    default_desc = qf.get("desc", "")
    default_loc = qf.get("loc", CAMPUS_LOCATIONS[0])
    loc_idx = CAMPUS_LOCATIONS.index(default_loc) if default_loc in CAMPUS_LOCATIONS else 0

    with st.form("form_report_lost"):
        col_1, col_2 = st.columns([2, 1])
        with col_1:
            lost_title = st.text_input("Item Title", value=default_title, placeholder="e.g. Lost Blue Milton Water Bottle")
        with col_2:
            lost_date = st.date_input("Date Lost", value=date.today())
            
        lost_desc = st.text_area(
            "Description (Any language)",
            value=default_desc,
            height=100,
            placeholder="e.g. Mera navy blue Milton water bottle 2nd floor library reading hall me chhut gaya..."
        )
        
        col_3, col_4 = st.columns(2)
        with col_3:
            lost_location = st.selectbox("Campus Location", options=CAMPUS_LOCATIONS, index=loc_idx)
        with col_4:
            lost_contact_email = st.text_input("Your Campus Email", value="student@campus.edu", placeholder="student@campus.edu")
            
        submit_lost = st.form_submit_button("Submit Lost Report", type="primary", use_container_width=True)

    if submit_lost:
        if not lost_title.strip() or not lost_desc.strip():
            st.error("Please provide both an Item Title and Description.")
        else:
            with st.spinner("Analyzing description with Sarvam AI..."):
                extracted_attrs, is_live, msg = extract_attributes_with_sarvam(
                    description=lost_desc,
                    location_hint=lost_location,
                    override_api_key=active_api_key
                )
                
                masked_email = lost_contact_email[:1] + "***@" + lost_contact_email.split("@")[-1] if "@" in lost_contact_email else "masked@campus.edu"
                new_report = {
                    "type": "lost",
                    "title": lost_title.strip(),
                    "raw_description": lost_desc.strip(),
                    "reported_location": lost_location,
                    "date": str(lost_date),
                    "contact": {
                        "name": "Student",
                        "email": masked_email,
                        "phone": "+91 98*** 00000",
                        "is_dummy": False
                    },
                    "attributes": extracted_attrs,
                    "extraction_metadata": {
                        "model_used": SARVAM_MODEL_NAME if is_live else "Offline Heuristic Parser (Demo Mode)",
                        "is_live_ai": is_live,
                        "status_message": msg
                    },
                    "status": "open"
                }
                
                saved = add_report(new_report)
                st.success(f"Report submitted. ID: {saved['id']}")
                if is_live:
                    st.info(msg)
                else:
                    st.warning(msg)
                    
                st.write(f"**Extracted**: {extracted_attrs.get('item_type')} • {extracted_attrs.get('color')} • Brand: {extracted_attrs.get('brand')} • Language: {extracted_attrs.get('detected_language')}")


# ==============================================================================
# SECTION 3: REPORT FOUND
# ==============================================================================
with tab_found:
    st.markdown("#### Report a Found Item")
    st.caption("Log items found on campus to help match them with owners.")
    
    with st.form("form_report_found"):
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            found_title = st.text_input("Item Title", placeholder="e.g. Found Casio Calculator, Blue Bottle")
        with col_f2:
            found_date = st.date_input("Date Found", value=date.today())
            
        found_desc = st.text_area(
            "Description (Any language)",
            height=100,
            placeholder="e.g. Found navy blue water bottle on 2nd floor library near cubicle..."
        )
        
        col_f3, col_f4 = st.columns(2)
        with col_f3:
            found_location = st.selectbox("Where was it found?", options=CAMPUS_LOCATIONS, index=1)
        with col_f4:
            found_contact_email = st.text_input("Finder/Desk Email", value="helpdesk@campus.edu")
            
        submit_found = st.form_submit_button("Submit Found Report", type="primary", use_container_width=True)

    if submit_found:
        if not found_title.strip() or not found_desc.strip():
            st.error("Please provide both an Item Title and Description.")
        else:
            with st.spinner("Analyzing description with Sarvam AI..."):
                extracted_attrs, is_live, msg = extract_attributes_with_sarvam(
                    description=found_desc,
                    location_hint=found_location,
                    override_api_key=active_api_key
                )
                
                masked_email = found_contact_email[:1] + "***@" + found_contact_email.split("@")[-1] if "@" in found_contact_email else "masked@campus.edu"
                new_report = {
                    "type": "found",
                    "title": found_title.strip(),
                    "raw_description": found_desc.strip(),
                    "reported_location": found_location,
                    "date": str(found_date),
                    "contact": {
                        "name": "Finder/Desk",
                        "email": masked_email,
                        "phone": "+91 90*** 00000",
                        "is_dummy": False
                    },
                    "attributes": extracted_attrs,
                    "extraction_metadata": {
                        "model_used": SARVAM_MODEL_NAME if is_live else "Offline Heuristic Parser (Demo Mode)",
                        "is_live_ai": is_live,
                        "status_message": msg
                    },
                    "status": "open"
                }
                
                saved = add_report(new_report)
                st.success(f"Report submitted. ID: {saved['id']}")
                if is_live:
                    st.info(msg)
                else:
                    st.warning(msg)
                    
                st.write(f"**Extracted**: {extracted_attrs.get('item_type')} • {extracted_attrs.get('color')} • Brand: {extracted_attrs.get('brand')} • Language: {extracted_attrs.get('detected_language')}")


# ==============================================================================
# SECTION 4: INVENTORY
# ==============================================================================
with tab_inventory:
    st.markdown("#### Campus Inventory")
    inventory = load_reports()
    
    col_i1, col_i2 = st.columns([3, 1])
    with col_i1:
        inv_search = st.text_input("Filter inventory", placeholder="Search items...", label_visibility="collapsed")
    with col_i2:
        filter_type = st.selectbox("Filter", ["All Items", "Lost Items Only", "Found Items Only"], label_visibility="collapsed")

    filtered = inventory
    if filter_type == "Lost Items Only":
        filtered = [r for r in filtered if r.get("type") == "lost"]
    elif filter_type == "Found Items Only":
        filtered = [r for r in filtered if r.get("type") == "found"]

    if inv_search.strip():
        s = inv_search.strip().lower()
        filtered = [
            r for r in filtered
            if s in r.get("title", "").lower() or s in r.get("raw_description", "").lower()
            or s in r.get("id", "").lower() or s in str(r.get("attributes", {})).lower()
        ]

    st.markdown(f"<div style='font-size: 0.85rem; color: #64748B; margin-bottom: 12px;'>Total: <b>{len(filtered)}</b> items</div>", unsafe_allow_html=True)
    
    for item in filtered:
        is_lost = item.get("type") == "lost"
        pill = '<span class="item-pill-lost">Lost</span>' if is_lost else '<span class="item-pill-found">Found</span>'
        attrs = item.get("attributes", {})
        
        with st.container():
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div>
                        {pill} <b>{item.get('title')}</b> <span style="font-size: 0.8rem; color: #94A3B8;">({item.get('id')})</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #94A3B8;">
                        {item.get('date')}
                    </div>
                </div>
                <div style="font-size: 0.85rem; color: #475569; margin: 4px 0;">
                    {item.get('raw_description')}
                </div>
                <div>
                    <span class="tag-chip">{attrs.get('item_type', 'Other')}</span>
                    <span class="tag-chip">{attrs.get('color', 'Unknown')}</span>
                    <span class="tag-chip">{attrs.get('location', item.get('reported_location'))}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"Actions for {item.get('id')}", expanded=False):
                if st.button("Delete Item", key=f"del_{item.get('id')}"):
                    delete_report(item.get("id"))
                    st.rerun()

st.markdown("<div style='text-align: center; font-size: 0.8rem; color: #94A3B8; margin-top: 30px;'>CampusFind • Simple Multilingual Lost & Found</div>", unsafe_allow_html=True)
