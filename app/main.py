from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
import logging
import re
import json

from app.adapters.semgrep import SemgrepAdapter
from app.defectdojo.client import DefectDojoClient
from app.storage import is_processed, mark_processed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
adapter = SemgrepAdapter()
dd_client = DefectDojoClient()

@app.post("/api/v1/import")
async def import_scan(
    scanner: str = Form(...),
    project: str = Form(...),
    branch: str = Form(...),
    commit: str = Form(...),
    pipeline_id: str = Form(...),
    report_file: UploadFile = File(...)
):
    if not re.match(r"^[a-zA-Z0-9_\-\/]+$", project):
        raise HTTPException(status_code=400, detail="Invalid project format")

    storage_key = f"{scanner}:{project}:{branch}:{commit}"
    
    if is_processed(storage_key):
        logger.info(f"Scan {storage_key} already exists. Skipping.")
        return {"status": "skipped", "reason": "Already processed"}

    try:
        content = await report_file.read()
        report_json = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in report file")

    data = {
        "scanner": scanner,
        "project": project,
        "branch": branch,
        "commit": commit,
        "report": report_json
    }

    payload = adapter.normalize(data)

    try:
        result = await dd_client.import_scan(payload)
        mark_processed(storage_key)
        return {"status": "ok", "action": "imported", "key": storage_key}
    except Exception as e:
        logger.error(f"DefectDojo error: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))
