"""Command-line sync. Equivalent to `python app.py --check`; kept for convenience."""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

if __name__ == "__main__":
    from app import main
    if len(sys.argv) == 1:
        sys.argv.append("--check")
    main()
