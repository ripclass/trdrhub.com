# apps/api/app/services/customs/customs_pack.py

import io
import json
import zipfile
from typing import Dict, Any


class CustomsPackBuilder:
    """
    Build a ZIP archive containing:
    - Extracted LC data (structured)
    - Extracted document data for all docs
    - A simple submission summary
    """

    def build_zip(self, validation_result: Dict[str, Any]) -> bytes:
        """
        validation_result = the final structured_result from the validator pipeline
        """
        mem = io.BytesIO()

        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            # 1) LC Data
            structured_result = validation_result.get("structured_result", {})
            if structured_result.get("lc_data"):
                z.writestr(
                    "LC.json",
                    json.dumps(structured_result["lc_data"], indent=2, ensure_ascii=False)
                )

            # 2) Document-level extracted data
            extracted_documents = structured_result.get("extracted_documents", {})
            for doc_name, doc_struct in extracted_documents.items():
                safe_name = doc_name.replace(".pdf", "").replace(" ", "_")
                z.writestr(
                    f"{safe_name}.json",
                    json.dumps(doc_struct, indent=2, ensure_ascii=False)
                )

            # 3) Submission summary (simple JSON now)
            processing_summary = structured_result.get("processing_summary", {})
            summary = {
                "total_documents": processing_summary.get("total_documents"),
                "lc_type": validation_result.get("lc_type"),
                "lc_compliance": processing_summary.get("compliance_rate"),
                "customs_ready": processing_summary.get("customs_ready_score"),
                "discrepancies": processing_summary.get("total_discrepancies"),
                "processing_time": processing_summary.get("processing_time_display"),
            }

            z.writestr("SubmissionSummary.json", json.dumps(summary, indent=2, ensure_ascii=False))

        return mem.getvalue()

