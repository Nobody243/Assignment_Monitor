# Assignment Monitor: new interface (prototype)

React + TypeScript + Vite. It talks to the app's engine (`engine.py`, repo root) over loopback HTTP; the Python code
(scraper, tracker, uploads, cloud checks) stays as it is and keeps its tests.

```bash
# 1. the engine, with a fixed dev port/token (127.0.0.1 only)
python engine.py --dev

# 2. the interface
cd ui && npm install && npm run dev      # http://localhost:5173
```

Without the engine the page shows clearly labelled sample data. Design notes are at the top of `src/index.css`.
Keys: Ctrl K search/commands, j / k move, u upload, Esc close.
