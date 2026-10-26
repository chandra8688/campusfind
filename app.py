"""
CampusFind - Multilingual Lost-and-Found Matching Website for College Campuses
Powered by Sarvam AI (Sarvam-105B) and Streamlit
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
    page_title="CampusFind — Smart Campus Lost & Found",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished campus portal aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Brand Hero */
    .hero-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F3554 100%);
        border-radius: 16px;
        padding: 24px 30px;
        color: white;
        margin-bottom: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 6px;
        background: linear-gradient(90deg, #38BDF8, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 14px;
        line-height: 1.5;
    }
    
    /* Status Badges */
    .status-badge-live {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .status-badge-demo {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Item Cards */
    .item-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }
    .item-card:hover {
        border-color: #94A3B8;
        box-shadow: 0 6px 12px rgba(0,0,0,0.06);
    }
    
    .pill-lost {
        background-color: #FEE2E2;
        color: #991B1B;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .pill-found {
        background-color: #D1FAE5;
        color: #065F46;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .attr-chip {
        background-color: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 500;
        display: inline-block;
        margin-right: 6px;
        margin-top: 4px;
    }
    
    .match-container {
        background: #F8FAFC;
        border: 2px solid #6366F1;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 22px;
    }
    
    .match-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    
    .score-circle {
        font-size: 1.3rem;
        font-weight: 800;
        color: #4F46E5;
        background: #EEF2FF;
        border: 2px solid #818CF8;
        padding: 6px 14px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "api_key_override" not in st.session_state:
        st.session_state.api_key_override = ""
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "matches"
    if "quick_fill_lost" not in st.session_state:
        st.session_state.quick_fill_lost = None
    if "quick_fill_found" not in st.session_state:
        st.session_state.quick_fill_found = None


init_session_state()

# Determine effective API Key (env var takes precedence or user session override)
env_key = get_sarvam_api_key()
active_api_key = env_key or st.session_state.api_key_override.strip()
is_live_key_configured = bool(active_api_key)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 🎓 CampusFind Portal")
    st.caption("Multilingual Lost & Found Intelligence for College Campuses")
    
    st.divider()
    
    # Engine Status & Key Config
    st.markdown("#### ⚡ AI Engine Status")
    if is_live_key_configured:
        masked = active_api_key[:4] + "..." + active_api_key[-4:] if len(active_api_key) > 8 else "***"
        st.markdown(
            f'<div class="status-badge-live">● Sarvam-105B Connected ({masked})</div>',
            unsafe_allow_html=True
        )
        st.caption("Live Sarvam-105B inference is active for attribute extraction.")
    else:
        st.markdown(
            '<div class="status-badge-demo">▲ Sample-Demo Mode Active</div>',
            unsafe_allow_html=True
        )
        st.caption("No `SARVAM_API_KEY` detected. Extraction runs via offline campus heuristic demo parser. Live AI is **not** used.")
    
    with st.expander("🔑 Sarvam API Key Settings", expanded=not is_live_key_configured):
        st.write("Optionally enter your Sarvam AI API Key to test live Sarvam-105B extraction:")
        input_key = st.text_input(
            "Sarvam API Key",
            type="password",
            value=st.session_state.api_key_override,
            placeholder="Paste your Sarvam API Key here",
            help="Key is kept in your temporary session and never written to disk."
        )
        if input_key != st.session_state.api_key_override:
            st.session_state.api_key_override = input_key
            st.rerun()
            
        st.markdown("[Get API Key from Sarvam AI](https://sarvam.ai)")

    st.divider()

    # Quick Stats
    all_reports = load_reports()
    lost_count = sum(1 for r in all_reports if r.get("type") == "lost")
    found_count = sum(1 for r in all_reports if r.get("type") == "found")
    potential_pairs = find_all_campus_matches(all_reports, min_score=40)
    
    st.markdown("#### 📊 Campus Stats")
    c1, c2, c3 = st.columns(3)
    c1.metric("Lost", lost_count)
    c2.metric("Found", found_count)
    c3.metric("Matches", len(potential_pairs))
    
    st.divider()

    # One-Click Demo Control
    st.markdown("#### 🚀 Demo Controls")
    if st.button("🔄 Reset / Reload Sample Data", use_container_width=True, help="Reloads realistic multilingual campus reports"):
        reset_to_samples()
        st.success("Sample campus reports reloaded!")
        st.rerun()

    st.divider()
    
    # Multilingual Quick-Fill Prompts
    st.markdown("#### 🌐 Try Multilingual Samples")
    st.caption("Click to load real campus lost-item scenarios:")
    
    if st.button("🇮🇳 Hinglish: Milton Water Bottle", use_container_width=True):
        st.session_state.quick_fill_lost = {
            "title": "Lost Milton Bottle near Library",
            "desc": "Mera navy blue Milton water bottle library ke second floor pe computer lab ke pass chhut gaya, uspar Spider-Man ka sticker hai.",
            "loc": "Central Library (1st/2nd Floor Reading Hall)"
        }
        st.info("Loaded into 'Report Lost Item' form!")

    if st.button("🇮🇳 Hindi: Casio fx-991EX Calculator", use_container_width=True):
        st.session_state.quick_fill_lost = {
            "title": "खोया: Casio fx-991EX कैलकुलेटर",
            "desc": "मैकेनिकल ब्लॉक रूम 102 में मेरा ब्लैक केसियो कैलकुलेटर छूट गया। पीछे रोल नंबर का स्टिकर लगा है।",
            "loc": "Mechanical & Civil Engineering Block"
        }
        st.info("Loaded into 'Report Lost Item' form!")

    if st.button("🇮🇳 Tamil-English: Student ID Card", use_container_width=True):
        st.session_state.quick_fill_lost = {
            "title": "Lost Student ID Card in Cafeteria",
            "desc": "Ennudaya Student ID card campus cafeteria billing counter kitta drop pannitten. Dark blue lanyard with CS department stamp.",
            "loc": "Campus Cafeteria & Food Court"
        }
        st.info("Loaded into 'Report Lost Item' form!")

    st.divider()
    st.caption("🔒 **Privacy & Safety**: Student phone numbers and emails are masked. Matches are algorithmic suggestions and require physical proof of ownership.")


# ----------------- MAIN HEADER -----------------
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🎓 CampusFind</div>
    <div class="hero-subtitle">
        Intelligent Multilingual Lost-and-Found Matching for College Campuses.<br>
        Report lost items in English, Hindi, Hinglish, Tamil, or Telugu. Sarvam-105B extracts structured item attributes to pinpoint matches instantly.
    </div>
</div>
""", unsafe_allow_html=True)


# ----------------- NAVIGATION TABS -----------------
tab_match, tab_lost, tab_found, tab_inventory, tab_about = st.tabs([
    "🔍 Find Potential Matches",
    "📢 Report Lost Item",
    "🎁 Report Found Item",
    "📋 Campus Inventory",
    "⚡ One-Click Demo & Docs"
])


# ==============================================================================
# TAB 1: FIND POTENTIAL MATCHES
# ==============================================================================
with tab_match:
    st.subheader("🎯 Potential Lost-to-Found Matches")
    st.caption("Matches are calculated via Python scoring across item category (40 pts), location (20 pts), color (15 pts), brand (15 pts), and distinctive features (10 pts).")
    
    reports = load_reports()
    
    # Filter Controls
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search_query = st.text_input("Filter matches by keyword", placeholder="e.g. Milton, Calculator, Library, ID Card, Blue", label_visibility="collapsed")
    with col_f2:
        min_threshold = st.slider("Minimum Match Score (%)", min_value=30, max_value=90, value=40, step=5)
    with col_f3:
        if st.button("⚡ Find Matches Now", use_container_width=True, type="primary"):
            st.rerun()

    matches = find_all_campus_matches(reports, min_score=min_threshold)
    
    if search_query.strip():
        q = search_query.strip().lower()
        matches = [
            m for m in matches
            if q in m["lost"]["title"].lower() or q in m["found"]["title"].lower()
            or q in m["lost"]["raw_description"].lower() or q in m["found"]["raw_description"].lower()
            or q in str(m["lost"]["attributes"]).lower() or q in str(m["found"]["attributes"]).lower()
        ]

    st.markdown(f"**Identified {len(matches)} Potential Pairings** (Score ≥ {min_threshold}%)")
    
    if not matches:
        st.info("No potential matches found at this threshold. Try lowering the score threshold slider or report new items.")
    else:
        for idx, match in enumerate(matches):
            res = match["match_result"]
            lost = match["lost"]
            found = match["found"]
            score = res["score"]
            conf_badge = res["confidence_badge"]
            conf_label = res["confidence_label"]
            
            # Match Card Container
            with st.container():
                st.markdown(f"""
                <div class="match-container">
                    <div class="match-header">
                        <div>
                            <span style="font-size: 1.15rem; font-weight: 700; color: #1E293B;">
                                {conf_badge} Potential Match #{idx+1} — {conf_label}
                            </span>
                            <div style="font-size: 0.85rem; color: #64748B; margin-top: 2px;">
                                Lost: <code>{lost.get('id')}</code> &nbsp;⟷&nbsp; Found: <code>{found.get('id')}</code>
                            </div>
                        </div>
                        <div class="score-circle">
                            {score}% Match
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Side-by-side comparison
                c_lost, c_found = st.columns(2)
                
                with c_lost:
                    st.markdown(f"**📢 LOST: {lost.get('title')}**")
                    st.markdown(f"<span class='pill-lost'>LOST REPORT</span> • Reported: {lost.get('date')}", unsafe_allow_html=True)
                    st.write(f"*{lost.get('raw_description')}*")
                    
                    l_attr = lost.get("attributes", {})
                    st.markdown(f"""
                    - **Item Type:** `{l_attr.get('item_type')}`
                    - **Color:** `{l_attr.get('color')}`
                    - **Brand:** `{l_attr.get('brand')}`
                    - **Location:** `{l_attr.get('location')}`
                    - **Distinctive Features:** {l_attr.get('distinctive_features')}
                    - **Language:** `{l_attr.get('detected_language')}`
                    """)
                    
                with c_found:
                    st.markdown(f"**🎁 FOUND: {found.get('title')}**")
                    st.markdown(f"<span class='pill-found'>FOUND REPORT</span> • Found: {found.get('date')}", unsafe_allow_html=True)
                    st.write(f"*{found.get('raw_description')}*")
                    
                    f_attr = found.get("attributes", {})
                    st.markdown(f"""
                    - **Item Type:** `{f_attr.get('item_type')}`
                    - **Color:** `{f_attr.get('color')}`
                    - **Brand:** `{f_attr.get('brand')}`
                    - **Location:** `{f_attr.get('location')}`
                    - **Distinctive Features:** {f_attr.get('distinctive_features')}
                    - **Language:** `{f_attr.get('detected_language')}`
                    """)

                # Scoring explanation breakdown
                with st.expander(f"🔍 Why did this match? ({score}/100 Breakdown)", expanded=False):
                    st.markdown("**Scoring Breakdown (Transparent Python Engine):**")
                    for factor in res["breakdown"]:
                        pts = factor["points"]
                        max_p = factor["max_points"]
                        pts_str = f"+{pts}" if pts > 0 else f"{pts}"
                        st.markdown(f"- **{factor['factor']}** ({pts_str}/{max_p} pts): {factor['detail']}")
                    
                    st.caption("⚠️ **Notice:** This is an algorithmically estimated potential match, not a confirmed ownership verification. Always verify serial numbers, roll numbers, or physical proof before item handover.")

                # Contact / Handover Modal Button
                with st.expander("📬 Contact / Handover Details", expanded=False):
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.markdown("**Lost Item Reporter (Owner):**")
                        c_l = lost.get("contact", {})
                        st.write(f"Name: {c_l.get('name', 'Anonymous Student')}")
                        st.write(f"Email: `{c_l.get('email', 'masked')}`")
                        st.write(f"Phone: `{c_l.get('phone', 'masked')}`")
                    with cc2:
                        st.markdown("**Found Item Finder / Helpdesk:**")
                        c_f = found.get("contact", {})
                        st.write(f"Name: {c_f.get('name', 'Campus Helpdesk')}")
                        st.write(f"Email: `{c_f.get('email', 'masked')}`")
                        st.write(f"Phone: `{c_f.get('phone', 'masked')}`")
                        
                    st.info("💡 **Safe Handover Tip**: Meet at the campus security desk or student welfare office during working hours.")

                st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)


# ==============================================================================
# TAB 2: REPORT LOST ITEM
# ==============================================================================
with tab_lost:
    st.subheader("📢 Report a Lost Item")
    st.caption("Describe what you lost in any language (English, Hindi, Hinglish, Tamil, Telugu, etc.). Sarvam-105B will extract structured attributes automatically.")
    
    # Pre-fill if quick-fill was clicked
    qf = st.session_state.quick_fill_lost or {}
    default_title = qf.get("title", "")
    default_desc = qf.get("desc", "")
    default_loc = qf.get("loc", CAMPUS_LOCATIONS[0])
    loc_idx = CAMPUS_LOCATIONS.index(default_loc) if default_loc in CAMPUS_LOCATIONS else 0

    with st.form("lost_item_form"):
        col_l1, col_l2 = st.columns([2, 1])
        with col_l1:
            lost_title = st.text_input(
                "Short Title *",
                value=default_title,
                placeholder="e.g. Lost Blue Milton Thermos Bottle, Black Casio Calculator"
            )
        with col_l2:
            lost_date = st.date_input("Date Lost *", value=date.today())

        lost_desc = st.text_area(
            "Item Description (Write in English, Hindi, Hinglish, etc.) *",
            value=default_desc,
            height=120,
            placeholder="e.g. Mera navy blue color ka Milton bottle reading hall me chhut gaya. Uspe superhero sticker hai aur steel cap hai."
        )

        col_l3, col_l4 = st.columns(2)
        with col_l3:
            lost_location = st.selectbox("Campus Location *", options=CAMPUS_LOCATIONS, index=loc_idx)
        with col_l4:
            lost_cat_hint = st.selectbox("Item Category", options=COMMON_CATEGORIES)

        st.markdown("##### 👤 Contact Details (Optional & Masked)")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            contact_name = st.text_input("Your Name", value="Student User", placeholder="e.g. Arjun Sharma")
        with col_c2:
            contact_email = st.text_input("Campus Email", value="student@campus.edu", placeholder="e.g. student@campus.edu")
        with col_c3:
            contact_phone = st.text_input("Mobile Number", value="+91 98765 43210", placeholder="e.g. +91 98765 43210")

        submit_lost = st.form_submit_button("🚀 Submit Lost Item & Extract Attributes", type="primary", use_container_width=True)

    if submit_lost:
        if not lost_title.strip() or not lost_desc.strip():
            st.error("Please fill in both the Title and Description fields.")
        else:
            with st.spinner("🤖 Sarvam AI is analyzing your description and extracting structured attributes..."):
                extracted_attrs, is_live, msg = extract_attributes_with_sarvam(
                    description=lost_desc,
                    location_hint=lost_location,
                    override_api_key=active_api_key
                )
                
                # Mask contact for privacy
                masked_email = contact_email[:1] + "***@" + contact_email.split("@")[-1] if "@" in contact_email else "masked@campus.edu"
                masked_phone = contact_phone[:6] + "*** " + contact_phone[-4:] if len(contact_phone) >= 10 else "+91 98*** 00000"
                
                new_report = {
                    "type": "lost",
                    "title": lost_title.strip(),
                    "raw_description": lost_desc.strip(),
                    "reported_location": lost_location,
                    "date": str(lost_date),
                    "contact": {
                        "name": contact_name.strip() or "Student User",
                        "email": masked_email,
                        "phone": masked_phone,
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
                st.success(f"✅ Lost Item Report successfully registered! ID: `{saved['id']}`")
                
                if is_live:
                    st.info(msg)
                else:
                    st.warning(msg)
                    
                # Display extracted attributes preview card
                st.markdown("#### 📋 Extracted Structured Attributes:")
                c_a1, c_a2, c_a3 = st.columns(3)
                c_a1.metric("Item Type", extracted_attrs.get("item_type"))
                c_a2.metric("Color", extracted_attrs.get("color"))
                c_a3.metric("Brand", extracted_attrs.get("brand"))
                
                st.markdown(f"""
                - **Distinctive Features:** {extracted_attrs.get('distinctive_features')}
                - **Extracted Location:** `{extracted_attrs.get('location')}`
                - **Detected Language:** `{extracted_attrs.get('detected_language')}`
                """)
                
                # Check immediate matches
                current_reports = load_reports()
                immediate_matches = find_matches_for_item(saved, current_reports, min_score=40)
                if immediate_matches:
                    st.markdown(f"### 🎯 Found {len(immediate_matches)} Potential Matches Immediately!")
                    for im in immediate_matches[:2]:
                        st.markdown(f"- **{im['score']}% Match**: Found item `{im['candidate']['id']}` — *{im['candidate']['title']}*")
                    st.info("Check the **'🔍 Find Potential Matches'** tab for full side-by-side details!")
                else:
                    st.info("No immediate matches found yet. We'll alert you as soon as someone reports a matching found item.")


# ==============================================================================
# TAB 3: REPORT FOUND ITEM
# ==============================================================================
with tab_found:
    st.subheader("🎁 Report a Found Item")
    st.caption("Did you find an item on campus? Help reunite it with its student owner. Multilingual reports supported.")
    
    with st.form("found_item_form"):
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            found_title = st.text_input(
                "Short Title *",
                placeholder="e.g. Found Blue Milton Bottle, Found Casio Calculator, Found Room Keys"
            )
        with col_f2:
            found_date = st.date_input("Date Found *", value=date.today())

        found_desc = st.text_area(
            "Item Description (Write in English, Hindi, Hinglish, etc.) *",
            height=120,
            placeholder="e.g. Found a navy blue water bottle on the second floor of the Central Library. It has a superhero sticker."
        )

        col_f3, col_f4 = st.columns(2)
        with col_f3:
            found_location = st.selectbox("Where was it found? *", options=CAMPUS_LOCATIONS, index=1)
        with col_f4:
            found_cat_hint = st.selectbox("Item Category", options=COMMON_CATEGORIES)

        st.markdown("##### 👤 Finder / Helpdesk Contact")
        col_fc1, col_fc2, col_fc3 = st.columns(3)
        with col_fc1:
            f_contact_name = st.text_input("Finder Name / Dept", value="Campus Security Helpdesk")
        with col_fc2:
            f_contact_email = st.text_input("Contact Email", value="helpdesk@campus.edu")
        with col_fc3:
            f_contact_phone = st.text_input("Contact Phone", value="+91 90000 00000")

        submit_found = st.form_submit_button("🚀 Submit Found Item & Extract Attributes", type="primary", use_container_width=True)

    if submit_found:
        if not found_title.strip() or not found_desc.strip():
            st.error("Please fill in both the Title and Description fields.")
        else:
            with st.spinner("🤖 Sarvam AI is analyzing your description and extracting structured attributes..."):
                extracted_attrs, is_live, msg = extract_attributes_with_sarvam(
                    description=found_desc,
                    location_hint=found_location,
                    override_api_key=active_api_key
                )
                
                masked_email = f_contact_email[:1] + "***@" + f_contact_email.split("@")[-1] if "@" in f_contact_email else "masked@campus.edu"
                masked_phone = f_contact_phone[:6] + "*** " + f_contact_phone[-4:] if len(f_contact_phone) >= 10 else "+91 90*** 00000"
                
                new_report = {
                    "type": "found",
                    "title": found_title.strip(),
                    "raw_description": found_desc.strip(),
                    "reported_location": found_location,
                    "date": str(found_date),
                    "contact": {
                        "name": f_contact_name.strip() or "Campus Helpdesk",
                        "email": masked_email,
                        "phone": masked_phone,
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
                st.success(f"✅ Found Item Report registered! ID: `{saved['id']}`")
                
                if is_live:
                    st.info(msg)
                else:
                    st.warning(msg)
                    
                st.markdown("#### 📋 Extracted Structured Attributes:")
                c_a1, c_a2, c_a3 = st.columns(3)
                c_a1.metric("Item Type", extracted_attrs.get("item_type"))
                c_a2.metric("Color", extracted_attrs.get("color"))
                c_a3.metric("Brand", extracted_attrs.get("brand"))
                
                st.markdown(f"""
                - **Distinctive Features:** {extracted_attrs.get('distinctive_features')}
                - **Extracted Location:** `{extracted_attrs.get('location')}`
                - **Detected Language:** `{extracted_attrs.get('detected_language')}`
                """)
                
                current_reports = load_reports()
                immediate_matches = find_matches_for_item(saved, current_reports, min_score=40)
                if immediate_matches:
                    st.markdown(f"### 🎯 Found {len(immediate_matches)} Potential Matches for this item!")
                    for im in immediate_matches[:2]:
                        st.markdown(f"- **{im['score']}% Match**: Lost item `{im['candidate']['id']}` — *{im['candidate']['title']}*")
                    st.info("Head to the **'🔍 Find Potential Matches'** tab to view side-by-side verification details!")


# ==============================================================================
# TAB 4: CAMPUS INVENTORY
# ==============================================================================
with tab_inventory:
    st.subheader("📋 Campus Lost & Found Inventory")
    st.caption("Browse all reported lost and found items stored in the local JSON repository.")
    
    inventory = load_reports()
    
    col_i1, col_i2, col_i3 = st.columns([2, 1, 1])
    with col_i1:
        inv_search = st.text_input("Search inventory", placeholder="Search by title, keyword, ID, brand...", label_visibility="collapsed")
    with col_i2:
        filter_type = st.selectbox("Status Filter", ["All Items", "Lost Items Only", "Found Items Only"])
    with col_i3:
        filter_cat = st.selectbox("Category Filter", ["All Categories"] + COMMON_CATEGORIES)

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

    st.markdown(f"Showing **{len(filtered)}** items:")
    
    for item in filtered:
        is_lost = item.get("type") == "lost"
        pill_html = '<span class="pill-lost">LOST</span>' if is_lost else '<span class="pill-found">FOUND</span>'
        attrs = item.get("attributes", {})
        meta = item.get("extraction_metadata", {})
        
        with st.container():
            st.markdown(f"""
            <div class="item-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        {pill_html} &nbsp; <strong>{item.get('title')}</strong> &nbsp;
                        <code style="color: #64748B;">{item.get('id')}</code>
                    </div>
                    <div style="font-size: 0.85rem; color: #64748B;">
                        📅 {item.get('date')}
                    </div>
                </div>
                <div style="margin: 10px 0; font-size: 0.95rem; color: #334155;">
                    <em>"{item.get('raw_description')}"</em>
                </div>
                <div>
                    <span class="attr-chip">🏷️ {attrs.get('item_type', 'Other')}</span>
                    <span class="attr-chip">🎨 {attrs.get('color', 'Unknown')}</span>
                    <span class="attr-chip">🏢 {attrs.get('brand', 'Unknown')}</span>
                    <span class="attr-chip">📍 {attrs.get('location', item.get('reported_location'))}</span>
                    <span class="attr-chip">🌐 {attrs.get('detected_language', 'English')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"⚙️ Details & Actions for {item.get('id')}", expanded=False):
                d1, d2 = st.columns([3, 1])
                with d1:
                    st.write(f"**Distinctive Features:** {attrs.get('distinctive_features', 'None')}")
                    st.write(f"**Contact:** {item.get('contact', {}).get('name')} ({item.get('contact', {}).get('email')})")
                    st.write(f"**Extracted via:** `{meta.get('model_used', 'sarvam-105b')}` | Live AI: `{meta.get('is_live_ai', False)}`")
                with d2:
                    if st.button(f"🗑️ Delete", key=f"del_{item.get('id')}"):
                        delete_report(item.get("id"))
                        st.warning(f"Deleted {item.get('id')}")
                        st.rerun()


# ==============================================================================
# TAB 5: ONE-CLICK DEMO & DOCS
# ==============================================================================
with tab_about:
    st.subheader("⚡ One-Click Demo & Technical Architecture")
    
    st.markdown("""
    ### 🎯 How CampusFind Works
    
    1. **Multilingual Ingestion**:
       - Students write lost or found reports in their natural language (English, Hindi, Hinglish, Tamil, Telugu, etc.).
    2. **Sarvam AI (Sarvam-105B) Extraction**:
       - Converts raw vernacular text into structured attributes:
         - `item_type` (normalized English category)
         - `color` (standardized colors)
         - `brand` (brand detection)
         - `distinctive_features` (stickers, scratches, roll numbers, keychains)
         - `location` (campus zone/building)
         - `detected_language`
       - If no `SARVAM_API_KEY` is provided, CampusFind activates **Sample-Demo Mode** using an intelligent offline heuristic parser, ensuring the app remains fully demonstrable without ever pretending to make a live API call.
    3. **Transparent Python Scoring Engine**:
       - Item Type match: **40 pts**
       - Campus Location proximity: **20 pts**
       - Color match: **15 pts**
       - Brand match: **15 pts**
       - Distinctive Features overlap: **10 pts**
       - Total Score: **0 - 100%** with complete explanation breakdown.
    4. **Safety & Privacy**:
       - Contact information is masked.
       - Matches are clearly labeled as unconfirmed potential suggestions to prevent fraudulent claims.
    """)
    
    st.divider()
    
    st.markdown("### 🧪 Pre-configured Demo Scenarios")
    st.markdown("""
    | Scenario | Lost Report (Language) | Found Report (Language) | Expected Match |
    |---|---|---|---|
    | **1. Water Bottle** | Hinglish (*"Mera blue Milton thermos bottle 2nd floor pe chhut gaya..."*) | English (*"Found navy blue Milton water bottle on 2nd floor..."*) | **100% Match** |
    | **2. Scientific Calc** | Hindi (*"मैकेनिकल ब्लॉक 102 में मेरा ब्लैक केसियो एफएक्स-991ईएक्स..."*) | Hinglish (*"Mechanical block tutorial hall ke pass black Casio calc mila..."*) | **96% Match** |
    | **3. Student ID** | Tamil/English (*"Student ID card campus cafeteria billing counter kitta drop..."*) | English (*"Found student identity card near cafeteria cash counter..."*) | **95% Match** |
    """)
    
    if st.button("🚀 Reload Default Demo Dataset", type="primary", use_container_width=True):
        reset_to_samples()
        st.success("Default multilingual dataset restored!")
        st.rerun()

st.markdown("<br><hr><center style='color: #94A3B8; font-size: 0.85rem;'>CampusFind MVP • Powered by Sarvam AI (Sarvam-105B) & Streamlit • Built for College Campuses</center>", unsafe_allow_html=True)
