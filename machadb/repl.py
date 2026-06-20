"""
repl.py — The Interactive Shell for MachaDB

Because every DB needs a way to type commands at 3 AM.
Features a beautiful prompt, error handling, and tabular output.
"""

import sys
import traceback

from .godaamu import MachaDB
from .errors import MachaError

try:
    import readline  # Provides history and line editing on Unix
except ImportError:
    pass  # Windows or no readline, adjust maadthide

def print_table(results: list, columns: list = None):
    """Format a list of dicts into an ASCII table."""
    if not results:
        print("Khali ide macha. (0 rows)")
        return
        
    if columns is None:
        columns = list(results[0].keys())
        
    # Calculate widths
    widths = {col: len(col) for col in columns}
    for row in results:
        for col in columns:
            val_str = str(row.get(col, ""))
            widths[col] = max(widths[col], len(val_str))
            
    # Print header
    header = "| " + " | ".join(col.ljust(widths[col]) for col in columns) + " |"
    separator = "|" + "-" * (len(header) - 2) + "|"
    
    print(separator)
    print(header)
    print(separator)
    
    # Print rows
    for row in results:
        line = "| " + " | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns) + " |"
        print(line)
        
    print(separator)
    print(f"({len(results)} rows)")

def start_repl(db_path: str = "./machadb_data"):
    """Start the interactive session."""
    print("=====================================================")
    print("☕ Welcome to MachaDB v1.0.0-chai-powered")
    print("Built by Bengaluru engineers who haven't slept.")
    print("Type 'sahaaya' for help, 'hogthini' to exit.")
    print("=====================================================")
    
    try:
        db = MachaDB(db_path)
    except Exception as e:
        print(f"Database open aaglilla macha! {e}")
        return

    while True:
        try:
            query = input("pydb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nhogthini macha, bye!")
            break
            
        if not query:
            continue
            
        if query.lower() in ("hogthini", "exit", "quit"):
            print("cya macha.")
            break
            
        try:
            result = db.execute(query)
            
            # Format output based on result type
            if isinstance(result, list):
                print_table(result)
            elif isinstance(result, str):
                print(result)
            else:
                print(result)
                
        except MachaError as e:
            # Print our custom slang errors nicely
            print(f"❌ {e}")
        except Exception as e:
            # For debugging true crashes
            print(f"❌ ayyo macha, Python crash aagthide: {e}")
            traceback.print_exc()

    db.close()

if __name__ == "__main__":
    start_repl()
