"""
Sarvam AI integration module using the official Python SDK (sarvamai).
Leverages Sarvam-105B to convert multilingual descriptions into structured attributes:
- item type
- color
- brand
- distinctive features
- location
- detected language
"""

import json
import re
from typing import Dict, Any, Tuple, Optional
from sarvamai import SarvamAI
from sarvamai.errors import ForbiddenError, UnauthorizedError
try:
    from sarvamai.core.api_error import ApiError
except ImportError:
    ApiError = Exception
from src.config import SARVAM_MODEL_NAME, get_sarvam_api_key

EXTRACTION_SYSTEM_PROMPT = """You are an accurate multilingual assistant for a college campus Lost-and-Found portal (CampusFind).
Your task is to analyze user-submitted descriptions (which may be written in English, Hindi, Hinglish, Tamil, Telugu, Kannada, Marathi, Bengali, or other Indian languages) and extract structured item attributes.

Extract strictly according to these rules:
1. "item_type": Standardized category in English (e.g., 'Water Bottle', 'Scientific Calculator', 'ID Card', 'Smartphone', 'Backpack', 'Earphones', 'Keys', 'Laptop', 'Smartwatch', 'Notebook', 'Glasses', 'Clothing', or 'Other').
2. "color": Primary color(s) in English (e.g., 'Blue', 'Navy Blue', 'Black', 'Silver', 'Red', 'White', or 'Unknown').
3. "brand": Brand name if mentioned (e.g., 'Milton', 'Casio', 'Wildcraft', 'Apple', 'Noise', 'Samsung', 'Boat', or 'Unknown').
4. "distinctive_features": Concrete unique features like stickers, engravings, cracks, scratches, keychains, covers, roll numbers, or 'None'.
5. "location": Specific campus location if mentioned in the text (e.g., 'Central Library 2nd Floor', 'Mechanical Block Room 102', 'Cafeteria', or 'Unknown').
6. "detected_language": Language of the input text (e.g., 'English', 'Hindi', 'Hinglish', 'Tamil', 'Telugu', etc.).

CRITICAL:
- Do NOT invent or hallucinate attributes not present or directly implied in the text.
- If an attribute is absent, set it to "Unknown" or "None".
- Respond ONLY with a valid JSON object. Do not add markdown explanation before or after.
"""

def extract_attributes_with_sarvam(
    description: str,
    location_hint: str = "",
    override_api_key: Optional[str] = None
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Extract structured attributes from item description using Sarvam-105B or demo parser.
    
    Returns:
        (attributes_dict, is_live_ai, status_message)
    """
    api_key = (override_api_key or get_sarvam_api_key()).strip()
    
    if not api_key:
        # Fallback to clearly identified offline demo extractor
        parsed = _offline_heuristic_extractor(description, location_hint)
        return (
            parsed,
            False,
            "⚠️ Sample-Demo Mode: Extracted via offline rule-based parser (No SARVAM_API_KEY configured). Live AI was NOT used."
        )

    try:
        # Initialize official SarvamAI client
        client = SarvamAI(api_subscription_key=api_key)
        
        user_prompt = f"Description: {description.strip()}"
        if location_hint:
            user_prompt += f"\nReported Form Location: {location_hint.strip()}"
            
        response = client.chat.completions(
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model=SARVAM_MODEL_NAME,
            temperature=0.1,
            max_tokens=400
        )
        
        if not response.choices or not response.choices[0].message:
            raise ValueError("Empty response received from Sarvam AI.")
            
        raw_text = response.choices[0].message.content or ""
        parsed = _parse_json_safely(raw_text)
        
        if not parsed:
            raise ValueError(f"Failed to parse structured JSON from Sarvam-105B output: {raw_text[:100]}")
            
        # Ensure all required keys exist
        attributes = _sanitize_attributes(parsed, location_hint)
        return (
            attributes,
            True,
            f"✅ Successfully extracted using Sarvam-105B (Official Sarvam AI API)"
        )
        
    except ForbiddenError as e:
        parsed = _offline_heuristic_extractor(description, location_hint)
        return (
            parsed,
            False,
            f"⚠️ Authentication Error (403): Invalid SARVAM_API_KEY. Using offline demo parser fallback."
        )
    except UnauthorizedError as e:
        parsed = _offline_heuristic_extractor(description, location_hint)
        return (
            parsed,
            False,
            f"⚠️ Authorization Error (401): Missing or expired SARVAM_API_KEY. Using offline demo parser fallback."
        )
    except ApiError as e:
        parsed = _offline_heuristic_extractor(description, location_hint)
        return (
            parsed,
            False,
            f"⚠️ Sarvam AI API Error: {str(e)[:150]}. Using offline demo parser fallback."
        )
    except Exception as e:
        parsed = _offline_heuristic_extractor(description, location_hint)
        return (
            parsed,
            False,
            f"⚠️ Connection/Processing notice ({type(e).__name__}): {str(e)[:100]}. Using offline demo parser fallback."
        )


def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Clean markdown backticks or extra text and load JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
        
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
        
    try:
        return json.loads(cleaned)
    except Exception:
        # Search for first { and last }
        match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                return None
        return None


def _sanitize_attributes(data: Dict[str, Any], fallback_location: str = "") -> Dict[str, Any]:
    """Ensure standard keys and types."""
    return {
        "item_type": str(data.get("item_type", "Other")).strip().title(),
        "color": str(data.get("color", "Unknown")).strip().title(),
        "brand": str(data.get("brand", "Unknown")).strip().title(),
        "distinctive_features": str(data.get("distinctive_features", "None")).strip(),
        "location": str(data.get("location") or fallback_location or "Unknown").strip(),
        "detected_language": str(data.get("detected_language", "English")).strip()
    }


def _offline_heuristic_extractor(description: str, location_hint: str = "") -> Dict[str, Any]:
    """
    Intelligent offline rule-based extractor for sample-demo mode
    when SARVAM_API_KEY is not configured.
    Explicitly labeled as non-live-AI.
    """
    desc_lower = description.lower()
    
    # 1. Item Type Heuristics
    item_type = "Other"
    if any(k in desc_lower for k in ["bottle", "thermos", "flask", "water"]):
        item_type = "Water Bottle"
    elif any(k in desc_lower for k in ["calculator", "casio", "fx-", "वैज्ञानिक कैलकुलेटर", "कैलकुलेटर"]):
        item_type = "Scientific Calculator"
    elif any(k in desc_lower for k in ["id card", "identity", "id", "lanyard", "आईडी कार्ड"]):
        item_type = "ID Card"
    elif any(k in desc_lower for k in ["backpack", "bag", "laptop bag", "बस्ता", "बैग"]):
        item_type = "Backpack"
    elif any(k in desc_lower for k in ["phone", "iphone", "samsung", "mobile", "smartphone", "फ़ोन", "मोबाइल"]):
        item_type = "Smartphone"
    elif any(k in desc_lower for k in ["earphones", "earbuds", "airpods", "headphones", "headset"]):
        item_type = "Earphones"
    elif any(k in desc_lower for k in ["keys", "keychain", "चाबी"]):
        item_type = "Keys"
    elif any(k in desc_lower for k in ["watch", "smartwatch", "घड़ी"]):
        item_type = "Smartwatch"
    elif any(k in desc_lower for k in ["laptop", "macbook", "dell", "hp", "लैपटॉप"]):
        item_type = "Laptop"
    elif any(k in desc_lower for k in ["notebook", "register", "copy", "कॉपी", "किताब"]):
        item_type = "Notebook"
    elif any(k in desc_lower for k in ["glasses", "spectacles", "chashma", "चश्मा"]):
        item_type = "Eyeglasses"

    # 2. Color Heuristics
    color = "Unknown"
    color_map = {
        "blue": ["blue", "navy", "neela", "नीला", "neelam"],
        "black": ["black", "kaala", "kala", "काला"],
        "grey": ["grey", "gray", "silver"],
        "red": ["red", "laal", "lal", "लाल"],
        "white": ["white", "safed", "सफेद"],
        "green": ["green", "hara", "हरा"],
        "yellow": ["yellow", "peela", "पीला"],
        "pink": ["pink", "gulabi", "गुलाबी"]
    }
    for col, keywords in color_map.items():
        if any(kw in desc_lower for kw in keywords):
            color = col.title()
            break

    # 3. Brand Heuristics
    brand = "Unknown"
    brands = [
        "Milton", "Casio", "Wildcraft", "Apple", "Noise", "Boat", "Sony",
        "Samsung", "Dell", "HP", "Lenovo", "Fastrack", "Tupperware", "Cello"
    ]
    for b in brands:
        if b.lower() in desc_lower:
            brand = b
            break

    # 4. Distinctive Features
    features = []
    if "sticker" in desc_lower or "स्टिकर" in desc_lower:
        if "batman" in desc_lower:
            features.append("Batman sticker")
        elif "superhero" in desc_lower:
            features.append("Superhero sticker")
        elif "roll" in desc_lower or "23me042" in desc_lower or "नंबर" in desc_lower:
            features.append("Roll number sticker")
        else:
            features.append("Distinctive sticker")
            
    if "lanyard" in desc_lower or "neck strap" in desc_lower:
        features.append("Neck lanyard / strap")
    if "keychain" in desc_lower or "football" in desc_lower:
        features.append("Keychain attached")
    if "crack" in desc_lower or "scratch" in desc_lower:
        features.append("Scratch/crack marks")
    if "thermosteel" in desc_lower or "stainless steel" in desc_lower:
        features.append("Stainless steel / thermosteel body")
        
    distinctive_features = ", ".join(features) if features else "None specifically highlighted"

    # 5. Language Detection
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', description))
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', description))
    has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', description))
    
    hinglish_words = ["mera", "meri", "mila", "chhut", "gaya", "gayi", "bahar", "kitta", "pe", "ka", "ki", "hai"]
    is_hinglish = any(w in desc_lower.split() for w in hinglish_words)

    if has_devanagari:
        detected_language = "Hindi (Devanagari)"
    elif has_tamil:
        detected_language = "Tamil"
    elif has_telugu:
        detected_language = "Telugu"
    elif is_hinglish:
        detected_language = "Hinglish (Hindi in Latin script)"
    else:
        detected_language = "English"

    # 6. Location
    location = location_hint or "Campus Premises"
    if "library" in desc_lower or "लाइब्रेरी" in desc_lower:
        location = "Central Library"
    elif "cafeteria" in desc_lower or "canteen" in desc_lower or "कैंटीन" in desc_lower:
        location = "Campus Cafeteria"
    elif "mech" in desc_lower or "mechanical" in desc_lower:
        location = "Mechanical Block"
    elif "sports" in desc_lower or "gym" in desc_lower or "badminton" in desc_lower:
        location = "Sports Complex / Gym"

    return {
        "item_type": item_type,
        "color": color,
        "brand": brand,
        "distinctive_features": distinctive_features,
        "location": location,
        "detected_language": detected_language
    }
