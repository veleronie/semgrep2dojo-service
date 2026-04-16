from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
    # 1. Валидация входных данных
    if not re.match(r"^[a-zA-Z0-9_\-\/]+$", project):
        raise HTTPException(status_code=400, detail="Invalid project format")

    # 2. Проверка на дубликаты
    storage_key = f"{scanner}:{project}:{branch}:{commit}"
    if is_processed(storage_key):
        logger.info(f"Scan {storage_key} already exists. Skipping.")
        return {"status": "skipped", "reason": "Already processed", "key": storage_key}

    try:
        # 3. Чтение и парсинг (с последующим закрытием дескриптора файла)
        try:
            content = await report_file.read()
            report_json = json.loads(content)
        finally:
            await report_file.close() # Важно для очистки временных файлов FastAPI
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in report file")
    except Exception as e:
        logger.error(f"File reading error: {e}")
        raise HTTPException(status_code=500, detail="Error processing uploaded file")

    # 4. Формирование данных для адаптера
    data = {
        "scanner": scanner,
        "project": project,
        "branch": branch,
        "commit": commit,
        "report": report_json
    }

    # 5. Трансформация (здесь происходит замена путей на ссылки из app.py)
    payload = adapter.normalize(data)

    # 6. Отправка в DefectDojo
    try:
        result = await dd_client.import_scan(payload)
        mark_processed(storage_key)
        logger.info(f"Successfully imported scan for {project} (commit: {commit})")
        return {"status": "ok", "action": "imported", "key": storage_key, "dojo_response": result}
    except Exception as e:
        logger.error(f"DefectDojo integration failed: {str(e)}")
        # Возвращаем 502 (Bad Gateway), так как проблема во внешнем сервисе (Dojo)
        raise HTTPException(status_code=502, detail=f"DefectDojo error: {str(e)}")