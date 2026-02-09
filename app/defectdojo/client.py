import json
import requests
from app.settings import DD_URL, DD_TOKEN, GIT_DOMAIN, REQUEST_TIMEOUT


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

    def import_scan(self, payload: dict):
        report = self._replace_locations(
            payload["file"],
            payload["product_name"],
            payload["branch_tag"],
        )

        if "results" in report and len(report["results"]) > 0:
            first_finding_path = report["results"][0].get("path")
            repo_url = first_finding_path if first_finding_path else f"{self._git_base()}/{payload['product_name']}"
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
            "auto_create_context": True,
            "close_old_findings": True,
            "close_old_findings_product_scope": True,
            "deduplication_on_engagement": True,
            "do_not_reactivate": True,
        }

        files = {
            "file": (
                "report.json",
                json.dumps(report),
                "application/json",
            )
        }

        r = requests.post(
            f"{DD_URL}/api/v2/import-scan/",
            headers={"Authorization": f"Token {DD_TOKEN}"},
            data=data,
            files=files,
            timeout=REQUEST_TIMEOUT,
        )

        if not r.ok:
            raise RuntimeError(f"DefectDojo error: {r.text}")

        return r.json()
