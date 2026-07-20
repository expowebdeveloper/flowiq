import importlib.util
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_json_py_path = os.path.join(os.path.dirname(_current_dir), "json", "json.py")

_spec = importlib.util.spec_from_file_location("loan_apply_json_verify", _json_py_path)
_local_json = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_local_json)

normalize_loan_type = _local_json.normalize_loan_type
load_requirements = _local_json.load_requirements


def get_required_documents(loan_type: str) -> dict:
    """
    Returns the applicant-wide and loan-category-specific document requirements
    for the given loan_type (e.g. "home_loan", "gold_loan"), keyed by the
    canonical category name from require.json (e.g. "Home Loan").
    """
    category = normalize_loan_type(loan_type)
    requirements = load_requirements()

    general_docs = requirements.get("applicant_requirements", {}).get("mandatory_documents", [])
    category_entry = requirements.get("loan_category_requirements", {}).get(category, {})
    category_docs = category_entry.get("mandatory_documents", [])
    category_fields = category_entry.get("mandatory_fields", [])

    return {
        "category": category or loan_type,
        "general_documents": general_docs,
        "category_documents": category_docs,
        "category_fields": category_fields,
    }
