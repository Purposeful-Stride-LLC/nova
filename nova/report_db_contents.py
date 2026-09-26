"""Extract and report database contents for GUI integration."""
from nova import db

def get_sample_records(table, limit=10):
    """Get sample records from a table for analysis."""
    con = db.connect()
    try:
        query = f"SELECT * FROM {table} ORDER BY id DESC LIMIT {limit}"
        rows = con.execute(query).fetchall()
        return [dict(row) for row in rows] if rows else []
    except Exception as e:
        print(f"Error reading {table}: {e}")
        return []
    finally:
        con.close()

def analyze_table(table):
    """Analyze a table structure and contents."""
    con = db.connect()
    try:
        # Get row count
        row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        
        # Get column names and sample data
        cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
        if not cols:
            return {}
            
        sample = get_sample_records(table, limit=5)
        
        # Analyze text columns
        analysis = {
            "name": table,
            "row_count": row_count,
            "columns": cols,
            "sample_data": sample[:3],  # Show first 3 records
            "has_text_cols": any("TEXT" in str(col[2]) for col in con.execute(f"PRAGMA table_info({table})").fetchall())
        }
        
        # Extract unique values from key TEXT columns if present
        if "description" in cols or "title" in cols:
            text_cols = [c for c in cols if c.lower() in ("description", "title", "body", "subject")]
            if text_cols:
                try:
                    unique_values = {}
                    for col in text_cols:
                        vals = con.execute(f"SELECT DISTINCT \"{col}\" FROM {table}").fetchall()
                        unique_values[col] = len(vals)
                    analysis["unique_text_entries"] = unique_values
                except:
                    pass
                    
        return analysis
    except Exception as e:
        return {"name": table, "error": str(e)}
    finally:
        con.close()

def generate_report():
    """Generate comprehensive database content report."""
    tables = ["observations", "queue", "facts", "jobs", "conversations", "turns",
               "reports", "employees", "packets", "hw_inv", "bites", "chunks"]
    
    print("=" * 80)
    print("NOVA DATABASE CONTENTS REPORT")
    print("Generated for GUI Integration Design")
    print("=" * 80)
    print()
    
    report = []
    for table in tables:
        analysis = analyze_table(table)
        if analysis and not analysis.get("error"):
            report.append(analysis)
            print(f"--- {table} (n={analysis['row_count']}) ---")
            if analysis.get("unique_text_entries"):
                for col, count in analysis["unique_text_entries"].items():
                    print(f"  {col}: {count} unique entries")
    return report

def read_gui_file(path):
    """Read existing GUI implementation."""
    try:
        with open(path) as f:
            return f.read()
    except Exception as e:
        return None

if __name__ == "__main__":
    tables = generate_report()
    
    print()
    print("=" * 80)
    print("GUI INTEGRATION ANALYSIS")
    print("=" * 80)
    print()
    
    # Read existing GUI files
    gui_app = read_gui_file("Documents/NOVA/NOVA_fieldkit_v1_4/nova/gui/app.py")
    gui_deck = read_gui_file("Documents/NOVA/NOVA_fieldkit_v1_4/nova/gui/deck.json")
    
    if gui_app:
        print("Existing GUI files detected:")
        print(f"  - app.py ({len(gui_app)} bytes)")
        print(f"  - deck.json present")
    
    # Summary of database content types suitable for GUI display
    print()
    print("=" * 80)
    print("CONTENT TYPES AVAILABLE FOR GUI DISPLAY")
    print("=" * 80)
    print()
    
    gui_content_map = {
        "observations": {"purpose": "Knowledge base / observations panel", "display_as": "List of insights with source attribution"},
        "facts": {"purpose": "Knowledge graph nodes", "display_as": "Cards or nodes in knowledge graph"},
        "queue": {"purpose": "Ingest backlog viewer", "display_as": "Progressive list with fetch status indicators"},
        "reports": {"purpose": "Report library / dashboard widgets", "display_as": "Filterable report cards with rank display"},
        "jobs": {"purpose": "Job scheduler monitor", "display_as": "Tile grid showing job status and frequency"},
        "turns": {"purpose": "Conversation history viewer", "display_as": "Timeline of dialogue turns"},
        "conversations": {"purpose": "Conversation list sidebar", "display_as": "List with subject/title preview"},
        "packets": {"purpose": "Message queue / communication log", "display_as": "Network traffic visualization"},
        "employees": {"purpose": "TTS worker status panel", "display_as": "Worker tiles with voice/model assignments"},
        "bites": {"purpose": "Audio snippet viewer", "display_as": "Waveform thumbnails with text transcript"},
    }
    
    print("Suggested GUI Components:")
    print("-" * 80)
    for table, info in gui_content_map.items():
        analysis = next((t for t in tables if t["name"] == table), {})
        count_str = f"(n={analysis.get('row_count', 'N/A')})"
        print(f"\n[{table.upper()}] {count_str}")
        print(f"  Role: {info['purpose']}")
        print(f"  Display: {info['display_as']}")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS FOR GUI ENHANCEMENT")
    print("=" * 80)
