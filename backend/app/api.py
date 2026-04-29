import traceback
from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .main import run_pipeline
except ImportError:
    from main import run_pipeline


app = FastAPI(title="University Aggregator API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    college_name: str = Field(..., min_length=1, description="University/college name")


runs_lock = Lock()
runs: dict[str, dict] = {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_run(run_id: str, college_name: str) -> None:
    try:
        result = run_pipeline(college_name=college_name, save_csv=True)
        finished_at = utc_now_iso()
        with runs_lock:
            runs[run_id]["status"] = result.get("status", "completed")
            runs[run_id]["updated_at"] = finished_at
            runs[run_id]["finished_at"] = finished_at
            runs[run_id]["result"] = result
    except Exception as exc:
        finished_at = utc_now_iso()
        with runs_lock:
            runs[run_id]["status"] = "failed"
            runs[run_id]["updated_at"] = finished_at
            runs[run_id]["finished_at"] = finished_at
            runs[run_id]["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/runs")
def create_run(payload: RunRequest) -> dict:
    college_name = payload.college_name.strip()
    if not college_name:
        raise HTTPException(status_code=400, detail="college_name cannot be empty")

    run_id = str(uuid4())
    now = utc_now_iso()

    with runs_lock:
        runs[run_id] = {
            "run_id": run_id,
            "college_name": college_name,
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "finished_at": None,
            "result": None,
            "error": None,
        }

    worker = Thread(target=execute_run, args=(run_id, college_name), daemon=True)
    worker.start()

    return {
        "run_id": run_id,
        "status": "running",
        "created_at": now,
        "college_name": college_name,
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    with runs_lock:
        run = runs.get(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run
