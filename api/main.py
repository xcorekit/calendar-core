# calendar-core/api/main.py
# FastAPI wrapper — scaffold only.
# Start: uvicorn api.main:app --reload
# ─────────────────────────────────────────────────────────────────────────────
# CHANGELOG (newest first)
# ─────────────────────────────────────────────────────────────────────────────
#   2026-04-30  Scaffolded
try:
    from fastapi import FastAPI
    from datetime import date
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
    from sconl_calendar import from_gregorian

    app = FastAPI(title="CalendarX API", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/equicycle/today")
    def equicycle_today():
        return from_gregorian(date.today())

except ImportError:
    print("Install: pip install sconl-calendarx[api]")
