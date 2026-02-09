from fastapi import FastAPI, HTTPException, Request
import logging
import re

from app.adapters.semgrep import SemgrepAdapter
from app.defectdojo.client import DefectDojoClient
from app.storage import is_processed, mark_processed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
adapter = SemgrepAdapter()
dd_client = DefectDojoClient()

@app.post("/api/v1/import")
async def import_scan(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    required_fields = ["scanner", "project", "branch", "commit", "pipeline_id", "report"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    if not re.match(r"^[a-zA-Z0-9_\-\/]+$", data["project"]):
        raise HTTPException(status_code=400, detail="Invalid project format")

    storage_key = f"{data['scanner']}:{data['project']}:{data['branch']}:{data['commit']}"
    
    if is_processed(storage_key):
        logger.info(f"Scan {storage_key} already exists in storage. Skipping.")
        return {"status": "skipped", "reason": "This commit has already been processed for this scanner/branch"}

    payload = adapter.normalize(data)

    try:
        result = dd_client.import_scan(payload)
        mark_processed(storage_key)
        return {"status": "ok", "action": "imported", "key": storage_key}
    except Exception as e:
        logger.error(f"DefectDojo error: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))