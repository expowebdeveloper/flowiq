from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
import json
import os
import importlib.util

from db import VerifiedPayload, get_session

# Dynamically load verify_loan_data from local json.py to avoid module name conflicts
current_dir = os.path.dirname(os.path.abspath(__file__))
json_py_path = os.path.join(current_dir, "json.py")

spec = importlib.util.spec_from_file_location("local_json_verify", json_py_path)
local_json = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_json)
verify_loan_data = local_json.verify_loan_data

router = APIRouter(prefix="/json-verify", tags=["json-verification"])

@router.post("")
async def verify_json_endpoint(
    file: Optional[UploadFile] = File(None),
    raw_json: Optional[str] = Form(None),
    verify: bool = Form(True),
):
    """
    Verifies loan application JSON data, or manually marks it unverified.
    The JSON data can be provided either by uploading a file or pasting raw JSON text.

    - verify=True: runs full verification (schema, eligibility, and document checks).
    - verify=False: bypasses verification and stores the payload as manually unverified.
    """
    data = None

    # 1. Parse from file if provided
    if file is not None and file.filename:
        try:
            content = await file.read()
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file format.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {e}")

    # 2. Parse from pasted raw JSON if no file is provided
    elif raw_json is not None and raw_json.strip():
        try:
            data = json.loads(raw_json.strip())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid raw JSON format.")

    # 3. If neither is provided, raise an error
    else:
        raise HTTPException(
            status_code=400,
            detail="Please provide loan application JSON data either by uploading a file or pasting raw JSON."
        )

    result = verify_loan_data(data, {"verify": verify})

    session = get_session()
    try:
        record = VerifiedPayload(
            payload_json=json.dumps(data),
            status=result["status"],
            errors=json.dumps(result.get("errors", [])),
            warnings=json.dumps(result.get("warnings", [])),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()

    return result
