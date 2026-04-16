class SemgrepAdapter:
    scan_type = "Semgrep JSON Report"

    def normalize(self, req):
        report = req["report"]
        project_path = req["project"].strip("/")
        
        parts = project_path.split("/")
        
        if len(parts) > 1:
            group = "/".join(parts[:-1]) # pipeline-project4/mobile
            name = parts[-1]             # android
        else:
            group = "Default"
            name = parts[0]

        return {
            "scan_type": self.scan_type,
            "product_type_name": group.lower(),
            "product_name": project_path.lower(),
            "engagement_name": "Semgrep Scan",
            "branch_tag": req["branch"],
            "commit_hash": req["commit"],
            "file": report,
        }