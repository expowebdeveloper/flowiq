import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db import get_db
from loan_recommendation.agent_commands.crud import UPLOAD_FOLDER, save_attachment, serialize_command
from loan_recommendation.agent_commands.schemas import AgentCommandCreate
from loan_recommendation.agent_commands.services import AgentCommandService

command_service = AgentCommandService()


def _parse_loan_types(loan_types: str) -> list[str]:
    return [t for t in loan_types.split(",") if t]


# Global requirements (bank_id always None) — powers the standalone "Loan
# Requirements" admin page. Also owns the edit/delete routes, since editing
# or deleting a requirement doesn't depend on whether it's global or
# bank-scoped (command_id alone is enough to look it up either way).
global_router = APIRouter(
    prefix="/agent-commands",
    tags=["Agent Commands"]
)


@global_router.get("")
def global_command_list(
    db: Session = Depends(get_db)
):
    commands = command_service.list_global_commands(db)
    return {
        "success": True,
        "commands": [serialize_command(c) for c in commands]
    }


@global_router.post("/add")
def create_global_command(
    scenario: str = Form(...),
    instruction: str = Form(...),
    loan_types: str = Form(""),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    stored_filename, original_filename = save_attachment(attachment)
    new_command = command_service.create_command(
        db=db,
        command=AgentCommandCreate(scenario=scenario, instruction=instruction, loan_types=_parse_loan_types(loan_types)),
        bank_id=None,
        attachment_filename=stored_filename,
        attachment_original_name=original_filename,
    )
    return {
        "success": True,
        "message": "Requirement added successfully.",
        "command_id": new_command.id if new_command else None
    }


@global_router.post("/{command_id}/edit")
def update_command(
    command_id: int,
    scenario: str = Form(...),
    instruction: str = Form(...),
    loan_types: str = Form(""),
    attachment: UploadFile | None = File(None),
    remove_attachment: bool = Form(False),
    db: Session = Depends(get_db)
):
    command = command_service.get_command(db=db, command_id=command_id)
    if not command:
        return {"success": False, "message": "Requirement not found."}

    stored_filename, original_filename = save_attachment(attachment)
    command_service.update_command(
        db=db,
        command=command,
        data=AgentCommandCreate(scenario=scenario, instruction=instruction, loan_types=_parse_loan_types(loan_types)),
        attachment_filename=stored_filename,
        attachment_original_name=original_filename,
        remove_attachment=remove_attachment,
    )
    return {
        "success": True,
        "message": "Requirement updated successfully."
    }


@global_router.get("/{command_id}/attachment")
def download_attachment(
    command_id: int,
    db: Session = Depends(get_db)
):
    command = command_service.get_command(db=db, command_id=command_id)
    if not command or not command.attachment_filename:
        raise HTTPException(status_code=404, detail="No attachment for this requirement.")

    file_path = os.path.join(UPLOAD_FOLDER, command.attachment_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Attachment file is missing on disk.")

    return FileResponse(
        file_path,
        filename=command.attachment_original_name or command.attachment_filename,
    )


@global_router.get("/{command_id}/delete")
@global_router.post("/{command_id}/delete")
def delete_command(
    command_id: int,
    db: Session = Depends(get_db)
):
    command = command_service.get_command(db=db, command_id=command_id)
    if not command:
        return {"success": False, "message": "Requirement not found."}

    command_service.delete_command(db=db, command=command)
    return {
        "success": True,
        "message": "Requirement deleted successfully."
    }


# Bank-scoped requirements — same underlying table, just filtered/created
# against a specific bank_id. Mounted under /banks alongside bank_management
# and loan_policy, following the same "/banks/{bank_id}/..." convention.
# Editing/deleting a bank-scoped requirement reuses the routes above.
bank_router = APIRouter(
    prefix="/banks",
    tags=["Agent Commands"]
)


@bank_router.get("/{bank_id}/commands")
def bank_command_list(
    bank_id: int,
    db: Session = Depends(get_db)
):
    commands = command_service.list_bank_commands(db=db, bank_id=bank_id)
    return {
        "success": True,
        "bank_id": bank_id,
        "commands": [serialize_command(c) for c in commands]
    }


@bank_router.post("/{bank_id}/commands/add")
def create_bank_command(
    bank_id: int,
    scenario: str = Form(...),
    instruction: str = Form(...),
    loan_types: str = Form(""),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    stored_filename, original_filename = save_attachment(attachment)
    new_command = command_service.create_command(
        db=db,
        command=AgentCommandCreate(scenario=scenario, instruction=instruction, loan_types=_parse_loan_types(loan_types)),
        bank_id=bank_id,
        attachment_filename=stored_filename,
        attachment_original_name=original_filename,
    )
    return {
        "success": True,
        "message": "Requirement added successfully.",
        "command_id": new_command.id if new_command else None
    }
