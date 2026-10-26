"""CampusFind Configuration and Environment Setup"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "reports.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Sarvam AI Model Configuration
SARVAM_MODEL_NAME = "sarvam-105b"

def get_sarvam_api_key() -> str:
    """Retrieve Sarvam API Key from environment variable or session override."""
    return os.getenv("SARVAM_API_KEY", "").strip()

# Campus Locations common on Indian College Campuses
CAMPUS_LOCATIONS = [
    "Central Library (Ground Floor)",
    "Central Library (1st/2nd Floor Reading Hall)",
    "Campus Cafeteria & Food Court",
    "Computer Science / IT Block",
    "Mechanical & Civil Engineering Block",
    "Electrical & Electronics Block",
    "Main Auditorium & Seminar Hall",
    "Sports Complex / Badminton Court / Gym",
    "Student Activity Center (SAC)",
    "Boys Hostel Block",
    "Girls Hostel Block",
    "Campus Administration Building",
    "College Bus Stand / Parking Lot",
    "Other Campus Location",
]

# Standard Item Categories
COMMON_CATEGORIES = [
    "Water Bottle / Flask",
    "Scientific Calculator",
    "ID Card / Wallet / Keys",
    "Smartphone / Tablet",
    "Backpack / Bag",
    "Earphones / Headphones",
    "Laptop & Accessories",
    "Smartwatch / Watch",
    "Eyeglasses / Sunglasses",
    "Notebook / Textbook",
    "Clothing / Jacket",
    "Other Miscellaneous",
]
