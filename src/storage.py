"""
Local JSON-based persistence storage for CampusFind reports.
Supports save, load, add, and one-click sample reset.
"""

import json
from typing import List, Dict, Any, Optional
from src.config import DATA_FILE, DATA_DIR
from src.samples import SAMPLE_REPORTS

def ensure_data_initialized() -> None:
    """Ensure data directory and file exist with initial sample data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0:
        save_reports(SAMPLE_REPORTS)

def load_reports() -> List[Dict[str, Any]]:
    """Load all lost and found reports from the local JSON file."""
    ensure_data_initialized()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return SAMPLE_REPORTS
    except Exception:
        save_reports(SAMPLE_REPORTS)
        return SAMPLE_REPORTS

def save_reports(reports: List[Dict[str, Any]]) -> None:
    """Save the list of reports to the local JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

def generate_report_id(reports: List[Dict[str, Any]]) -> str:
    """Generate next sequential ID like RPT-2026-009."""
    max_num = 0
    for r in reports:
        rid = r.get("id", "")
        if rid.startswith("RPT-2026-"):
            try:
                num = int(rid.replace("RPT-2026-", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"RPT-2026-{max_num + 1:03d}"

def add_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new report, assign an ID, and persist to JSON."""
    reports = load_reports()
    if not report.get("id"):
        report["id"] = generate_report_id(reports)
    reports.insert(0, report)
    save_reports(reports)
    return report

def reset_to_samples() -> List[Dict[str, Any]]:
    """Restore default multilingual sample reports."""
    save_reports(SAMPLE_REPORTS)
    return SAMPLE_REPORTS

def delete_report(report_id: str) -> bool:
    """Delete a report by its ID."""
    reports = load_reports()
    updated = [r for r in reports if r.get("id") != report_id]
    if len(updated) != len(reports):
        save_reports(updated)
        return True
    return False
