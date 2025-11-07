from typing import Any, Dict
from datetime import datetime


def build_final_output(config: dict, cleaned_data: dict, quality_report: dict) -> dict:
    metadata = config.get("metadata", {})
    if "date_extraction" in metadata:
        metadata["date_extraction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "nb_resultats" in  metadata:
        total_results = 0
        for items in cleaned_data.values():
            total_results += len(items)
        metadata["nb_resultats"] = total_results

    data_object = cleaned_data.copy()
    data_object["metadata"] = metadata

    final_report = {}
    num_collections = len(quality_report)
    if num_collections == 1:
        final_report = list(quality_report.values())[0]
    elif num_collections > 1:
        final_report = quality_report.copy()
        summary_total = 0
        summary_complete = 0
        for report in quality_report.values():
            summary_total += report.get("total_items", 0)
            summary_complete += report.get("complete_items", 0)

        summary_rate = 0
        if summary_total > 0:
            summary_rate = round(summary_complete / summary_total, 3)

        final_report["summary"] = {
            "total_items": summary_total,
            "complete_items": summary_complete,
            "completion_rate": summary_rate
        }

    output = {
        "status": "success",
        "data" : data_object,
        "quality_report": final_report
    }
    return output
