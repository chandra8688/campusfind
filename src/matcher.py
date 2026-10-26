"""
Matching engine for CampusFind.
Calculates a transparent compatibility score (0-100) between Lost and Found reports
based on:
1. Item Type (40 pts)
2. Location (20 pts)
3. Color (15 pts)
4. Brand (15 pts)
5. Distinctive Features (10 pts)

Important: Results are labeled strictly as unconfirmed potential matches.
"""

from typing import Dict, Any, List, Tuple
import re

# Synonym and category grouping map to handle realistic variations
TYPE_SYNONYMS = {
    "water bottle": ["bottle", "flask", "thermos", "water flask", "sipper", "water bottle / flask"],
    "scientific calculator": ["calculator", "casio calculator", "calc", "fx-991ex"],
    "id card": ["identity card", "id", "campus id", "student card", "college id", "smart card"],
    "smartphone": ["phone", "mobile", "iphone", "android", "cell phone"],
    "backpack": ["bag", "college bag", "laptop bag", "rucksack"],
    "earphones": ["headphones", "airpods", "earbuds", "tws", "earphones / headphones"],
    "keys": ["keychain", "room key", "bike key", "keys / keychain"],
    "smartwatch": ["watch", "fitness band", "wrist watch", "smartwatch / watch"],
    "laptop": ["macbook", "notebook pc", "computer", "laptop & accessories"],
    "eyeglasses": ["glasses", "spectacles", "sunglasses", "chashma", "goggles"],
}

LOCATION_KEYWORDS = {
    "library": ["library", "reading hall", "stack room", "study area", "circulation"],
    "cafeteria": ["cafeteria", "canteen", "food court", "mess", "snack counter"],
    "mechanical": ["mech", "mechanical", "workshop", "thermodynamics"],
    "computer science": ["cs", "cse", "it", "computer lab", "programming lab"],
    "sports": ["sports", "gym", "badminton", "basketball", "ground", "stadium"],
    "hostel": ["hostel", "hall of residence", "dorm"],
    "auditorium": ["auditorium", "seminar hall", "oat", "open air theater"],
}

def _clean_str(val: Any) -> str:
    if not val:
        return ""
    return str(val).strip().lower()

def _are_types_compatible(t1: str, t2: str) -> Tuple[bool, bool]:
    """
    Returns (exact_match, category_match).
    """
    c1, c2 = _clean_str(t1), _clean_str(t2)
    if not c1 or not c2:
        return (False, False)
    if c1 == c2:
        return (True, True)
    
    # Check synonymous groups
    for group_key, synonyms in TYPE_SYNONYMS.items():
        all_terms = [group_key] + synonyms
        m1 = any(term in c1 or c1 in term for term in all_terms)
        m2 = any(term in c2 or c2 in term for term in all_terms)
        if m1 and m2:
            return (False, True)
            
    return (False, False)

def _are_locations_compatible(l1: str, l2: str) -> Tuple[bool, float]:
    """
    Returns (is_match, match_ratio)
    """
    s1, s2 = _clean_str(l1), _clean_str(l2)
    if not s1 or not s2 or s1 == "unknown" or s2 == "unknown":
        return (False, 0.0)
    if s1 == s2:
        return (True, 1.0)
    if s1 in s2 or s2 in s1:
        return (True, 0.8)
        
    for zone, kws in LOCATION_KEYWORDS.items():
        in_s1 = any(kw in s1 for kw in kws)
        in_s2 = any(kw in s2 for kw in kws)
        if in_s1 and in_s2:
            return (True, 0.75)
            
    return (False, 0.0)

def _extract_feature_tokens(text: str) -> set:
    """Extract significant descriptive keywords ignoring stopwords."""
    stopwords = {"and", "with", "the", "for", "has", "have", "some", "none", "side", "back", "front", "small", "big", "a", "an", "on", "in", "of"}
    words = re.findall(r'[a-zA-Z0-9]+', _clean_str(text))
    return {w for w in words if len(w) > 2 and w not in stopwords}

def compute_match_score(lost_report: Dict[str, Any], found_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a transparent match score (0-100) and detailed explanation between
    a Lost report and a Found report.
    """
    lost_attr = lost_report.get("attributes", {})
    found_attr = found_report.get("attributes", {})
    
    breakdown = []
    total_score = 0
    
    # 1. Item Type (40 Points Max)
    lost_type = lost_attr.get("item_type", "")
    found_type = found_attr.get("item_type", "")
    exact_type, cat_type = _are_types_compatible(lost_type, found_type)
    
    if exact_type:
        type_pts = 40
        breakdown.append({
            "factor": "Item Type",
            "points": type_pts,
            "max_points": 40,
            "status": "exact",
            "detail": f"Exact item match: '{lost_type}'"
        })
    elif cat_type:
        type_pts = 30
        breakdown.append({
            "factor": "Item Type",
            "points": type_pts,
            "max_points": 40,
            "status": "partial",
            "detail": f"Related item category: '{lost_type}' ~ '{found_type}'"
        })
    else:
        type_pts = 0
        breakdown.append({
            "factor": "Item Type",
            "points": 0,
            "max_points": 40,
            "status": "mismatch",
            "detail": f"Different item categories ('{lost_type}' vs '{found_type}')"
        })
        
    total_score += type_pts
    
    # If item types completely conflict, match is impossible
    if type_pts == 0:
        return {
            "score": 0,
            "confidence_label": "No Match",
            "confidence_badge": "⚪",
            "breakdown": breakdown,
            "summary": "Item types do not match.",
            "is_viable": False
        }

    # 2. Location (20 Points Max)
    lost_loc = lost_attr.get("location") or lost_report.get("reported_location", "")
    found_loc = found_attr.get("location") or found_report.get("reported_location", "")
    loc_match, loc_ratio = _are_locations_compatible(lost_loc, found_loc)
    
    if loc_match:
        loc_pts = int(20 * loc_ratio)
        breakdown.append({
            "factor": "Location",
            "points": loc_pts,
            "max_points": 20,
            "status": "match",
            "detail": f"Compatible campus area: '{lost_loc}' & '{found_loc}'"
        })
        total_score += loc_pts
    else:
        breakdown.append({
            "factor": "Location",
            "points": 0,
            "max_points": 20,
            "status": "neutral",
            "detail": f"Different or unspecified locations ('{lost_loc}' vs '{found_loc}')"
        })

    # 3. Color (15 Points Max)
    lost_col = _clean_str(lost_attr.get("color", "unknown"))
    found_col = _clean_str(found_attr.get("color", "unknown"))
    
    if lost_col != "unknown" and found_col != "unknown":
        if lost_col == found_col or lost_col in found_col or found_col in lost_col:
            total_score += 15
            breakdown.append({
                "factor": "Color",
                "points": 15,
                "max_points": 15,
                "status": "match",
                "detail": f"Color match: '{lost_attr.get('color')}'"
            })
        else:
            breakdown.append({
                "factor": "Color",
                "points": 0,
                "max_points": 15,
                "status": "mismatch",
                "detail": f"Different colors reported ('{lost_attr.get('color')}' vs '{found_attr.get('color')}')"
            })
    else:
        # One or both unknown -> neutral +5
        total_score += 5
        breakdown.append({
            "factor": "Color",
            "points": 5,
            "max_points": 15,
            "status": "neutral",
            "detail": "Color neutral / not fully specified"
        })

    # 4. Brand (15 Points Max)
    lost_brand = _clean_str(lost_attr.get("brand", "unknown"))
    found_brand = _clean_str(found_attr.get("brand", "unknown"))
    
    if lost_brand != "unknown" and found_brand != "unknown":
        if lost_brand == found_brand or lost_brand in found_brand or found_brand in lost_brand:
            total_score += 15
            breakdown.append({
                "factor": "Brand",
                "points": 15,
                "max_points": 15,
                "status": "match",
                "detail": f"Matching brand: '{lost_attr.get('brand')}'"
            })
        else:
            # Different explicit brands - deduct 5 penalty
            total_score = max(0, total_score - 5)
            breakdown.append({
                "factor": "Brand",
                "points": -5,
                "max_points": 15,
                "status": "mismatch",
                "detail": f"Different brands reported ('{lost_attr.get('brand')}' vs '{found_attr.get('brand')}')"
            })
    else:
        # Neutral if brand unknown
        breakdown.append({
            "factor": "Brand",
            "points": 0,
            "max_points": 15,
            "status": "neutral",
            "detail": "Brand unmentioned in one or both reports"
        })

    # 5. Distinctive Features (10 Points Max)
    lost_feat = lost_attr.get("distinctive_features", "")
    found_feat = found_attr.get("distinctive_features", "")
    
    tokens_lost = _extract_feature_tokens(lost_feat + " " + lost_report.get("raw_description", ""))
    tokens_found = _extract_feature_tokens(found_feat + " " + found_report.get("raw_description", ""))
    shared_tokens = tokens_lost.intersection(tokens_found)
    
    # Exclude common tokens already counted in type/color
    ignore_tokens = {lost_type.lower(), found_type.lower(), lost_col, found_col, lost_brand, found_brand}
    meaningful_overlap = [t for t in shared_tokens if t not in ignore_tokens]
    
    if meaningful_overlap:
        feat_pts = min(10, 4 + len(meaningful_overlap) * 3)
        total_score += feat_pts
        breakdown.append({
            "factor": "Distinctive Features",
            "points": feat_pts,
            "max_points": 10,
            "status": "match",
            "detail": f"Shared unique descriptors: {', '.join(meaningful_overlap[:3])}"
        })
    elif lost_feat.lower() not in ["none", "unknown", ""] or found_feat.lower() not in ["none", "unknown", ""]:
        breakdown.append({
            "factor": "Distinctive Features",
            "points": 0,
            "max_points": 10,
            "status": "neutral",
            "detail": "Distinctive features do not directly correlate"
        })
        
    final_score = max(0, min(100, total_score))
    
    if final_score >= 70:
        conf_label = "Strong Potential Match"
        conf_badge = "🟢"
    elif final_score >= 45:
        conf_label = "Moderate Potential Match"
        conf_badge = "🟡"
    else:
        conf_label = "Low Probability Match"
        conf_badge = "⚪"
        
    return {
        "score": final_score,
        "confidence_label": conf_label,
        "confidence_badge": conf_badge,
        "breakdown": breakdown,
        "is_viable": final_score >= 35,
        "lost_id": lost_report.get("id"),
        "found_id": found_report.get("id")
    }

def find_matches_for_item(
    target_report: Dict[str, Any],
    all_reports: List[Dict[str, Any]],
    min_score: int = 40
) -> List[Dict[str, Any]]:
    """
    Find best matching candidates for a specific lost or found report.
    If target is 'lost', compares against all 'found'.
    If target is 'found', compares against all 'lost'.
    """
    target_type = target_report.get("type", "").lower()
    opposite_type = "found" if target_type == "lost" else "lost"
    
    matches = []
    for other in all_reports:
        if other.get("type", "").lower() != opposite_type:
            continue
            
        lost = target_report if target_type == "lost" else other
        found = other if target_type == "lost" else target_report
        
        result = compute_match_score(lost, found)
        if result["score"] >= min_score:
            matches.append({
                "match_result": result,
                "candidate": other,
                "target": target_report,
                "score": result["score"]
            })
            
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches

def find_all_campus_matches(
    reports: List[Dict[str, Any]],
    min_score: int = 40
) -> List[Dict[str, Any]]:
    """
    Scan entire campus inventory to find all high-confidence Lost-to-Found pairings.
    """
    lost_items = [r for r in reports if r.get("type") == "lost"]
    found_items = [r for r in reports if r.get("type") == "found"]
    
    all_pairs = []
    for lost in lost_items:
        for found in found_items:
            res = compute_match_score(lost, found)
            if res["score"] >= min_score:
                all_pairs.append({
                    "score": res["score"],
                    "match_result": res,
                    "lost": lost,
                    "found": found
                })
                
    all_pairs.sort(key=lambda x: x["score"], reverse=True)
    return all_pairs
