"""Command-line hourly reminder. Equivalent to `python app.py --remind`; kept for convenience."""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

if __name__ == "__main__":
    from app import main
    sys.argv = [sys.argv[0], "--remind"] + [a for a in sys.argv[1:] if a == "--test"]
    main()
