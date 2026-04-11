"""
Test CSV Column Mapping
────────────────────────────────────────────────────────────
Tests if the database correctly maps NYC Open Data CSV columns.
Run this after downloading your CSVs to verify mapping works.
"""

import csv
import sys
from pathlib import Path

# Test CSV column detection
def test_csv_columns(csv_file: str, benefit_type: str):
    """
    Show what columns are in the CSV and how they'll be mapped.
    """
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        return False
    
    print(f"\n{'='*70}")
    print(f" TESTING: {benefit_type.upper()}")
    print(f" File: {csv_file}")
    print(f"{'='*70}\n")
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        # Show columns
        print("COLUMNS IN CSV:")
        for i, col in enumerate(reader.fieldnames, 1):
            print(f"  {i:2}. {col}")
        
        # Test mapping on first row
        print(f"\n{'─'*70}")
        print(" MAPPING TEST (First Row)")
        print(f"{'─'*70}\n")
        
        first_row = next(reader, None)
        if not first_row:
            print("❌ CSV is empty!")
            return False
        
        # Simulate mapping
        from database import DatabaseManager
        db = DatabaseManager()
        mapped = db._map_csv_columns(first_row)
        
        print("MAPPED FIELDS:")
        for key in ['name', 'address', 'borough', 'phone', 'latitude', 'longitude', 'zip']:
            value = mapped.get(key, '❌ NOT FOUND')
            status = "✓" if mapped.get(key) else "✗"
            print(f"  {status} {key:12} → {value}")
        
        # Check metadata
        standard_keys = ['facility name', 'street address', 'borough', 
                        'phone number(s)', 'latitude', 'longitude',
                        'name', 'address', 'phone', 'postcode', 'post code',
                        'zip', 'zipcode']
        
        metadata_keys = [k for k in first_row.keys() 
                        if k.lower() not in standard_keys and first_row[k]]
        
        print(f"\nMETADATA FIELDS ({len(metadata_keys)}):")
        for key in metadata_keys[:5]:  # Show first 5
            print(f"  • {key}: {first_row[key][:50]}...")
        if len(metadata_keys) > 5:
            print(f"  ... and {len(metadata_keys) - 5} more")
        
        # Check required fields
        print(f"\n{'─'*70}")
        print(" VALIDATION")
        print(f"{'─'*70}\n")
        
        required = ['name', 'address', 'borough', 'latitude', 'longitude']
        missing = [f for f in required if not mapped.get(f)]
        
        if missing:
            print(f"❌ MISSING REQUIRED FIELDS: {', '.join(missing)}")
            print("\nTroubleshooting:")
            print("  1. Check if these columns exist in CSV (different name?)")
            print("  2. Check if values are empty in the CSV")
            print("  3. May need to add column name mapping in database.py")
            return False
        else:
            print("✓ All required fields mapped successfully!")
            
            # Check coordinates
            try:
                lat = float(mapped['latitude'])
                lon = float(mapped['longitude'])
                
                # NYC bounds check (rough)
                if 40.4 < lat < 41.0 and -74.3 < lon < -73.7:
                    print(f"✓ Coordinates valid: ({lat:.4f}, {lon:.4f})")
                else:
                    print(f"⚠ Coordinates outside NYC: ({lat:.4f}, {lon:.4f})")
            except (ValueError, TypeError):
                print(f"❌ Coordinates not numeric: lat={mapped['latitude']}, lon={mapped['longitude']}")
                return False
            
            return True


def main():
    """Test all benefit CSVs."""
    
    tests = [
        ("data/locations/snap_locations.csv", "snap"),
        ("data/locations/medicaid_offices.csv", "medicaid"),
        ("data/locations/hra_centers.csv", "hra_cash"),
    ]
    
    print("\n" + "="*70)
    print(" COMPASS NYC — CSV COLUMN MAPPING TEST")
    print("="*70)
    
    results = {}
    
    for csv_file, benefit_type in tests:
        passed = test_csv_columns(csv_file, benefit_type)
        results[benefit_type] = passed
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70 + "\n")
    
    for benefit_type, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:8} {benefit_type}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All CSVs validated! Run setup.py to populate database.")
    else:
        print("\n❌ Some CSVs failed validation. Fix issues above before running setup.py")
    
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())