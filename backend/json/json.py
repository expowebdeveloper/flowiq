import json
import os
from typing import Dict, Any

REQUIRE_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "require.json")

def load_requirements() -> Dict[str, Any]:
    """
    Loads the loan requirements from require.json.
    """
    if not os.path.exists(REQUIRE_JSON_PATH):
        raise FileNotFoundError(f"Requirements file not found at {REQUIRE_JSON_PATH}")
    with open(REQUIRE_JSON_PATH, "r") as f:
        return json.load(f)

def normalize_loan_type(lt: str) -> str:
    """
    Normalizes input loan type string to one of the canonical categories:
    Gold Loan, Vehicle Loan, Home Loan, Personal Loan, Education Loan.
    """
    if not lt:
        return ""
    lt_lower = lt.lower().strip()
    if "gold" in lt_lower:
        return "Gold Loan"
    if "vehicle" in lt_lower or "car" in lt_lower or "bike" in lt_lower or "vihicle" in lt_lower:
        return "Vehicle Loan"
    if "home" in lt_lower or "house" in lt_lower or "property" in lt_lower or "construction" in lt_lower or "mortgage" in lt_lower:
        return "Home Loan"
    if "personal" in lt_lower:
        return "Personal Loan"
    if "education" in lt_lower or "study" in lt_lower or "student" in lt_lower:
        return "Education Loan"
    return ""

def verify_loan_data(data: Dict[str, Any], options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Verifies the input loan application data against require.json.
    Supports categorization (Gold Loan, Vehicle Loan, Home Loan, Personal Loan, Education Loan).
    
    The 'options' parameter acts as the option key/configuration dictionary:
      - options["verify"] (bool, default True): Set to False to bypass verification (unverify).
      - options["check_eligibility"] (bool, default True): Set to False to skip bank eligibility checks.
      - options["strict_documents"] (bool, default True): Set to False to skip bank-specific document checks.
    """
    if options is None:
        options = {}
        
    should_verify = options.get("verify", True)
    check_eligibility = options.get("check_eligibility", True)
    strict_documents = options.get("strict_documents", True)
    
    if not should_verify:
        return {
            "is_verified": False,
            "status": "unverified",
            "message": "Verification bypassed (option key 'verify' was set to False).",
            "errors": [],
            "warnings": []
        }
        
    try:
        requirements = load_requirements()
    except Exception as e:
        return {
            "is_verified": False,
            "status": "error",
            "errors": [f"Failed to load require.json: {e}"],
            "warnings": []
        }
        
    errors = []
    warnings = []
    
    # 1. Verify General Applicant Mandatory Fields
    applicant_reqs = requirements.get("applicant_requirements", {})
    mandatory_fields = applicant_reqs.get("mandatory_fields", [])
    for field_info in mandatory_fields:
        field_key = field_info["field"]
        field_label = field_info["label"]
        
        # Support fallback mappings for address, name, email
        val = data.get(field_key)
        if val is None or str(val).strip() == "":
            if field_key == "applicant_name" and "first_name" in data:
                # Merge first_name and last_name as fallback
                val = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            elif field_key == "applicant_email" and "email" in data:
                val = data.get("email")
            elif field_key == "address" and "address_line_1" in data:
                # Merge address components as fallback
                val = f"{data.get('address_line_1', '')}, {data.get('city', '')}, {data.get('state', '')} {data.get('zip_code', '')}".strip()
                
        if val is None or str(val).strip() == "":
            errors.append(f"Missing mandatory field: {field_label} ({field_key})")
            
    # 2. Verify General Applicant Mandatory Documents
    provided_documents = data.get("documents", [])
    # Normalize document names for comparison
    normalized_provided_docs = [str(d).strip().lower() for d in provided_documents]
    
    mandatory_docs = applicant_reqs.get("mandatory_documents", [])
    for doc_info in mandatory_docs:
        doc_name = doc_info["document"]
        if doc_name.lower() not in normalized_provided_docs:
            errors.append(f"Missing mandatory document: {doc_name}")
            
    # 3. Category-Specific Validation
    loan_type_input = data.get("loan_type")
    loan_category = normalize_loan_type(loan_type_input)
    
    if loan_category:
        cat_reqs = requirements.get("loan_category_requirements", {}).get(loan_category, {})
        
        # Verify category-specific mandatory fields
        cat_fields = cat_reqs.get("mandatory_fields", [])
        for field_info in cat_fields:
            field_key = field_info["field"]
            field_label = field_info["label"]
            
            # Add fallbacks for Home Loan property value
            val = data.get(field_key)
            if val is None or str(val).strip() == "":
                if field_key == "property_value" and "purchase_price" in data:
                    val = data.get("purchase_price")
                elif field_key == "property_address" and "address_line_1" in data:
                    val = f"{data.get('address_line_1', '')}, {data.get('city', '')}, {data.get('state', '')} {data.get('zip_code', '')}".strip()
                    
            if val is None or str(val).strip() == "":
                errors.append(f"[{loan_category}] Missing mandatory field: {field_label} ({field_key})")
                
        # Verify category-specific mandatory documents
        cat_docs = cat_reqs.get("mandatory_documents", [])
        for doc_info in cat_docs:
            doc_name = doc_info["document"]
            if doc_name.lower() not in normalized_provided_docs:
                errors.append(f"[{loan_category}] Missing mandatory document: {doc_name}")
    else:
        if loan_type_input:
            warnings.append(f"Unrecognized loan type '{loan_type_input}'; skipping category-specific validations.")
            
    # 4. Verify Bank-Specific Criteria by Category
    bank_name = data.get("bank_name")
    if bank_name:
        bank_criteria = requirements.get("bank_eligibility_criteria", {})
        if bank_name in bank_criteria:
            all_criteria = bank_criteria[bank_name]
            
            # Resolve criteria for resolved category (defaulting to Home Loan if not resolved to match general behavior)
            resolved_cat = loan_category if loan_category else "Home Loan"
            criteria = all_criteria.get(resolved_cat)
            
            if criteria:
                if check_eligibility:
                    # Credit Score Check (Checking 'credit_score' or 'fico_score')
                    score_val = data.get("credit_score") if "credit_score" in data else data.get("fico_score")
                    if score_val is not None and str(score_val).strip() != "":
                        try:
                            credit_score = int(score_val)
                            min_score = criteria.get("min_credit_score", 0)
                            if credit_score < min_score:
                                errors.append(
                                    f"[{resolved_cat}] Credit score ({credit_score}) is below {bank_name}'s minimum requirement of {min_score}."
                                )
                        except ValueError:
                            errors.append("Field 'credit_score' or 'fico_score' must be an integer.")
                    else:
                        warnings.append(f"Credit score not provided; skipping score eligibility for {bank_name}.")
                        
                    # Monthly Income Check (Checking 'monthly_income')
                    income_val = data.get("monthly_income")
                    if income_val is not None and str(income_val).strip() != "":
                        try:
                            monthly_income = float(income_val)
                            min_income = criteria.get("min_monthly_income", 0.0)
                            if monthly_income < min_income:
                                errors.append(
                                    f"[{resolved_cat}] Monthly income ({monthly_income}) is below {bank_name}'s minimum requirement of {min_income}."
                                )
                        except ValueError:
                            errors.append("Field 'monthly_income' must be a numeric value.")
                    else:
                        warnings.append(f"Monthly income not provided; skipping income eligibility for {bank_name}.")
                        
                    # Loan Amount Check (Checking 'loan_amount' or 'purchase_price')
                    amt_val = data.get("loan_amount") if "loan_amount" in data else data.get("purchase_price")
                    if amt_val is not None and str(amt_val).strip() != "":
                        try:
                            loan_amount = float(amt_val)
                            max_loan = criteria.get("max_loan_amount_limit", float('inf'))
                            if loan_amount > max_loan:
                                errors.append(
                                    f"[{resolved_cat}] Requested loan amount ({loan_amount}) exceeds {bank_name}'s limit of {max_loan}."
                                )
                        except ValueError:
                            errors.append("Field 'loan_amount' or 'purchase_price' must be a numeric value.")
                    else:
                        warnings.append(f"Loan amount not provided; skipping loan amount limit verification for {bank_name}.")
                        
                # Bank required documents for this category
                if strict_documents:
                    bank_docs = criteria.get("required_documents", [])
                    for b_doc in bank_docs:
                        if b_doc.lower() not in normalized_provided_docs:
                            errors.append(f"[{resolved_cat}] Missing bank-required document for {bank_name}: {b_doc}")
            else:
                warnings.append(f"{bank_name} does not have criteria defined for category '{resolved_cat}'. Skipping eligibility checks.")
        else:
            warnings.append(f"Bank '{bank_name}' not found in requirements criteria database. Skipping eligibility checks.")
            
    is_verified = len(errors) == 0
    
    return {
        "is_verified": is_verified,
        "status": "verified" if is_verified else "failed",
        "errors": errors,
        "warnings": warnings
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python json.py <path_to_data.json> [options_json_string]")
        sys.exit(1)
        
    data_path = sys.argv[1]
    opts = {}
    if len(sys.argv) > 2:
        try:
            opts = json.loads(sys.argv[2])
        except Exception as e:
            print(f"Error parsing options JSON: {e}")
            sys.exit(1)
            
    try:
        with open(data_path, "r") as file:
            input_data = json.load(file)
        result = verify_loan_data(input_data, opts)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
