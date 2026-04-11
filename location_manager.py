"""
Compass NYC — Location Manager
────────────────────────────────────────────────────────────
Structured filtering and formatting of service locations.
No RAG needed here — just SQL queries and deterministic logic.
"""

from typing import List, Dict, Optional
from database import DatabaseManager
from config import BOROUGHS


class LocationManager:
    """
    Manages service location data with structured filtering.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def get_locations(self, benefit_type: str, borough: Optional[str] = None) -> List[Dict]:
        """
        Get all locations for a benefit, optionally filtered by borough.
        
        Args:
            benefit_type: e.g., "snap", "medicaid"
            borough: e.g., "brooklyn", "manhattan" (case-insensitive)
        
        Returns:
            List of location dicts with all fields
        """
        locations = self.db.load_locations(benefit_type, borough)
        print(f"[Locations] Loaded {len(locations)} locations for '{benefit_type}'"
              + (f" in {borough}" if borough else ""))
        return locations
    
    def detect_borough(self, query: str) -> Optional[str]:
        """
        Simple keyword detection for borough names in user query.
        Returns None if no borough detected.
        """
        query_lower = query.lower()
        for borough in BOROUGHS:
            if borough in query_lower:
                return borough
        return None
    
    def format_for_prompt(self, locations: List[Dict], max_locations: int = 10) -> str:
        """
        Format locations as clean structured text for LLM prompt.
        
        Args:
            locations: List of location dicts
            max_locations: Limit number shown (avoid huge prompts)
        
        Returns:
            Formatted string ready for prompt injection
        """
        if not locations:
            return "No service locations found for the specified area."
        
        # Limit to prevent prompt overflow
        locations = locations[:max_locations]
        
        formatted_lines = []
        for i, loc in enumerate(locations, 1):
            lines = [
                f"{i}. {loc['name']}",
                f"   Address  : {loc['address']}, {loc['borough']} {loc['zip']}",
            ]
            
            if loc.get('phone'):
                lines.append(f"   Phone    : {loc['phone']}")
            if loc.get('hours'):
                lines.append(f"   Hours    : {loc['hours']}")
            if loc.get('walk_in'):
                lines.append(f"   Walk-in  : {loc['walk_in']}")
            if loc.get('languages'):
                lines.append(f"   Languages: {loc['languages']}")
            
            formatted_lines.append("\n".join(lines))
        
        result = "\n\n".join(formatted_lines)
        
        if len(self.db.load_locations(locations[0].get('benefit_type', ''))) > max_locations:
            result += f"\n\n(Showing {max_locations} of {len(locations)} total locations)"
        
        return result
    
    def format_for_map(self, locations: List[Dict]) -> List[Dict]:
        """
        Format locations for map display (frontend).
        Returns list of dicts with standardized fields.
        """
        map_data = []
        for loc in locations:
            map_data.append({
                "name": loc.get('name', 'Unknown'),
                "address": loc.get('address', ''),
                "borough": loc.get('borough', ''),
                "latitude": loc.get('latitude'),
                "longitude": loc.get('longitude'),
                "phone": loc.get('phone', ''),
                "hours": loc.get('hours', ''),
                "category": loc.get('category', 'general'),  # from benefit config
                "color": loc.get('color', '#666666'),  # from benefit config
            })
        return map_data


# ── CONVENIENCE FUNCTION ──────────────────────────────────────────────────────

def get_location_context(benefit_type: str, query: str) -> tuple[str, List[Dict]]:
    """
    One-liner to get both formatted text and raw location data.
    
    Returns:
        (formatted_text_for_prompt, raw_locations_for_map)
    """
    manager = LocationManager()
    borough = manager.detect_borough(query)
    locations = manager.get_locations(benefit_type, borough)
    formatted_text = manager.format_for_prompt(locations)
    return formatted_text, locations


if __name__ == "__main__":
    # Test location retrieval
    manager = LocationManager()
    
    # Test borough detection
    query1 = "I live in Brooklyn and need help with food"
    print(f"Query: {query1}")
    print(f"Detected borough: {manager.detect_borough(query1)}\n")
    
    # Test location retrieval
    locations = manager.get_locations("snap", "brooklyn")
    
    print("\n" + "="*70)
    print(" FORMATTED LOCATIONS")
    print("="*70)
    print(manager.format_for_prompt(locations))
    print("="*70)