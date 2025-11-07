from typing import Any, Dict
from datetime import datetime


def build_final_output(config: dict, cleaned_data: dict, quality_report: dict) -> dict:
    """
    Build the final output report including cleaned data and quality report.
    Args:
        config (dict): The original configuration including metadata.
        cleaned_data (dict): The cleaned data collected from scraping.
        quality_report (dict): The quality report for each collection.
    Returns:
        dict: The final output report.
    """
    metadata = config.get("metadata", {})
    if "date_extraction" in metadata:
        metadata["date_extraction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "nb_resultats" in  metadata:
        total_results = 0
        for items in cleaned_data.values():
            total_results += len(items)
        metadata["nb_resultats"] = total_results

    data_object = cleaned_data.copy() # data object is already a dict of collections, only need to add metadata
    data_object["metadata"] = metadata # Add metadata to the data object

    final_report = {}
    num_collections = len(quality_report)
    # If only one collection, simplify the report structure
    if num_collections == 1:
        final_report = list(quality_report.values())[0] 
    #If several collections for example "teeshirts" and "pants"
    elif num_collections > 1:
        final_report = quality_report.copy()
        summary_total = 0
        summary_complete = 0
        # For each collection, aggregate totals for summary
        for report in quality_report.values():
            summary_total += report.get("total_items", 0)
            summary_complete += report.get("complete_items", 0)

        summary_rate = 0
        if summary_total > 0:
            summary_rate = round(summary_complete / summary_total, 3)

        # We have several collections, add a summary of all
        final_report["summary"] = {
            "total_items": summary_total,
            "complete_items": summary_complete,
            "completion_rate": summary_rate
        }

    #constructh the final output
    output = {
        "status": "success",
        "data" : data_object,
        "quality_report": final_report
    }
    return output
