import json, re
from app.settings import GIT_DOMAIN

class SemgrepAdapter:
    scan_type = "Semgrep JSON Report"

    def normalize(self, req):
        report = req["report"]
        parts = req["project"].split("/")
        group = "/".join(parts[:-1])        # namespace
        project = req["project"].lower()
        return {
            "scan_type": self.scan_type,
            "product_type_name": group.lower(),
            "product_name": project,
            "engagement_name": f"{self.scan_type} scan",
            "branch_tag": req["branch"],
            "commit_hash": req["commit"],
            "file": report,
        }


