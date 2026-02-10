import json
import httpx
import logging
from app.settings import DD_URL, DD_TOKEN, GIT_DOMAIN, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

class DefectDojoClient:

    def _git_base(self) -> str:
        if GIT_DOMAIN.startswith("http"):
            return GIT_DOMAIN.rstrip("/")
        return f"https://{GIT_DOMAIN}"

    def _replace_locations(self, report: dict, project: str, branch: str) -> dict:

        base_url = f"{self._git_base()}/{project}/-/blob/{branch}"

        if "results" not in report:
            return report

        for finding in report["results"]:
            file_path = finding.get("path")
            if not file_path or file_path.startswith("http"):
                continue

            line = finding.get("start", {}).get("line", 1)
            finding["path"] = f"{base_url}/{file_path}#L{line}"

        return report

    async def import_scan(self, payload: dict):
        report = self._replace_locations(
            payload["file"],
            payload["product_name"],
            payload["branch_tag"],
        )

        # 2. Логика определения URL репозитория
        if "results" in report and len(report["results"]) > 0:
            first_finding_path = report["results"][0].get("path")
            repo_url = first_finding_path if (first_finding_path and "://" in first_finding_path) else f"{self._git_base()}/{payload['product_name']}"
        else:
            repo_url = f"{self._git_base()}/{payload['product_name']}"
        data = {
            "scan_type": payload["scan_type"],
            "product_type_name": payload["product_type_name"],
            "product_name": payload["product_name"],
            "engagement_name": payload["engagement_name"],
            "branch_tag": payload["branch_tag"],
            "commit_hash": payload["commit_hash"],
            "source_code_management_uri": repo_url,
            "auto_create_context": "true",
            "close_old_findings": "true",
            "close_old_findings_product_scope": "true",
            "deduplication_on_engagement": "true",
            "do_not_reactivate": "true",
        }

        files = {
            "file": (
                "report.json",
                json.dumps(report),
                "application/json",
            )
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                r = await client.post(
                    f"{DD_URL}/api/v2/import-scan/",
                    headers={"Authorization": f"Token {DD_TOKEN}"},
                    data=data,
                    files=files,
                )
                
                if r.status_code not in [200, 201]:
                    logger.error(f"DefectDojo error response: {r.text}")
                    raise RuntimeError(f"DefectDojo error: {r.status_code} - {r.text}")

                return r.json()
                
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
                raise RuntimeError(f"Connection error to DefectDojo: {str(exc)}")
