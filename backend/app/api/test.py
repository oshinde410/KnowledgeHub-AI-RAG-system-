from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from app.api.deps import get_db


router = APIRouter()


@router.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))

    return {
        "status": result.scalar()
    }


@router.get("/health/memory")
def memory_health():
    """Return simple memory usage stats for the process.

    Tries `psutil` first, otherwise reads `/proc/self/status` on Linux.
    """
    try:
        import psutil

        p = psutil.Process()
        mem = p.memory_info()
        return {
            "rss": mem.rss,
            "vms": getattr(mem, "vms", None),
        }
    except Exception:
        # Fallback: try /proc/self/status (Linux)
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        # value in kB
                        kb = int(parts[1])
                        return {"rss": kb * 1024}
        except Exception:
            pass

    return {"error": "memory info unavailable"}