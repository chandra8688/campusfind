# 🎓 CampusFind — Multilingual Lost-and-Found Matching for College Campuses

> **An intelligent, multilingual lost-and-found matching portal built for university campuses.** Powered by **Sarvam AI (Sarvam-105B)** and **Streamlit**.

---

## 🌟 Overview

Campus life is inherently multilingual. A student might post in Hindi (*"Mera blue Milton thermos library me chhut gaya"*), while a staff member logs a found report in English (*"Found navy blue water flask on 2nd floor"*). Traditional keyword search fails across language barriers and varied phrasing.

**CampusFind** solves this using **Sarvam-105B**:
1. **Multilingual Attribute Extraction**: Converts vernacular descriptions (Hindi, Hinglish, Tamil, Telugu, English) into standardized structured attributes (`item_type`, `color`, `brand`, `distinctive_features`, `location`, `detected_language`).
2. **Transparent Python Scoring Engine**: Computes compatibility scores (0–100%) based on weighted campus matching rules with transparent explanations.
3. **Safety & Privacy First**: Masks student emails and phone numbers; marks matches as unconfirmed potential leads rather than definitive claims.
4. **Offline Sample-Demo Mode**: If no `SARVAM_API_KEY` is provided, the application runs seamlessly in clearly labeled demo mode with an offline heuristic parser, ensuring 100% testability anytime.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend & UI** | Streamlit + Custom CSS | Responsive campus portal design with custom badge components and side-by-side cards |
| **Multilingual AI** | Sarvam AI Python SDK (`sarvamai`) | `sarvam-105b` chat completion model for structured attribute extraction |
| **Matching Engine** | Pure Python Scoring | Weighted rubric: Item Type (40), Location (20), Color (15), Brand (15), Features (10) |
| **Persistence** | Local JSON Storage | `data/reports.json` with auto-save, reload, and one-click demo dataset reset |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed
- (Optional) Sarvam AI API Key from [https://sarvam.ai/](https://sarvam.ai/)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Sarvam AI API Key (Optional)
CampusFind reads your API key from the `SARVAM_API_KEY` environment variable:

**On Windows (PowerShell):**
```powershell
$env:SARVAM_API_KEY="your-sarvam-api-key-here"
```

**On Linux / macOS:**
```bash
export SARVAM_API_KEY="your-sarvam-api-key-here"
```

> **Note:** If no key is set, the application automatically runs in **Sample-Demo Mode** using an intelligent offline heuristic parser. You can also enter an API key temporarily directly within the app sidebar!

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Testing the Complete Workflow

1. **One-Click Demo**:
   - Navigate to the **"⚡ One-Click Demo & Docs"** tab or click **"🔄 Reset / Reload Sample Data"** in the sidebar.
   - Pre-loaded pairs demonstrate cross-lingual matches:
     - **Hinglish** Lost Water Bottle ⟷ **English** Found Water Flask (**100% Match**)
     - **Pure Devanagari Hindi** Lost Calculator ⟷ **Hinglish** Found Calculator (**96% Match**)
     - **Tamil-English** Lost Student ID ⟷ **English** Found Student ID (**95% Match**)
2. **Report a Lost Item**:
   - Go to the **"📢 Report Lost Item"** tab.
   - Write a description in Hindi or English (or click any sample prompt in the sidebar).
   - Submit to watch Sarvam-105B extract structured attributes.
3. **Find Potential Matches**:
   - Switch to **"🔍 Find Potential Matches"**.
   - Use the slider to filter by match percentage.
   - Expand the **"Why did this match?"** accordion to view the transparent point-by-point breakdown.
4. **Inspect Campus Inventory**:
   - Browse, search, filter, or delete items in the **"📋 Campus Inventory"** tab.

---

## 🧮 Matching Scoring Rubric

The compatibility engine computes a 0–100 score based on 5 verified criteria:

1. **Item Type (40 Points Max)**:
   - Identical category (e.g., *Water Bottle* == *Water Bottle*): **+40 pts**
   - Related synonym (e.g., *Flask* ~ *Water Bottle*): **+30 pts**
   - Conflicting category (e.g., *Laptop* vs *Bottle*): **0 pts (Disqualified)**
2. **Campus Location (20 Points Max)**:
   - Same building/floor: **+20 pts**
   - Same campus zone (e.g., Library reading hall vs study section): **+15 pts**
3. **Color (15 Points Max)**:
   - Matching color token (e.g., *Navy Blue* & *Blue*): **+15 pts**
   - Unspecified / neutral: **+5 pts**
4. **Brand (15 Points Max)**:
   - Matching brand (e.g., *Milton* == *Milton*, *Casio* == *Casio*): **+15 pts**
   - Conflicting brand: **-5 penalty**
5. **Distinctive Features (10 Points Max)**:
   - Shared unique keywords (e.g., *superhero sticker*, *roll number*, *lanyard*): **+4 to +10 pts**

---

## 📁 Repository Structure

```
├── app.py                 # Streamlit web application & user interface
├── requirements.txt       # Project dependencies
├── .gitignore             # Git ignore file excluding secrets and cache
├── README.md              # Project documentation
├── data/
│   └── reports.json       # Local JSON persistence store
└── src/
    ├── __init__.py
    ├── config.py          # Campus constants & API configuration
    ├── sarvam_client.py   # Sarvam AI (Sarvam-105B) integration & fallback parser
    ├── matcher.py         # Transparent Python scoring algorithm
    ├── storage.py         # JSON database operations & ID generator
    └── samples.py         # Seed multilingual realistic campus reports
```

---

## 🔒 Privacy & Safety Guidelines

- **Masked Contact Information**: Email and phone numbers are masked by default (`a***@campus.edu`, `+91 98*** 12345`).
- **Unconfirmed Matching Status**: Matches are labeled as *Potential Matches* to ensure claimants provide physical verification before handover.
- **Recommended Handover Locations**: Students are advised to conduct item handovers at campus security desks or student welfare offices.
