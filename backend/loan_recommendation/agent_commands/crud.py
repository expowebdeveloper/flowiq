import os
import shutil
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from loan_recommendation.models import AgentCommand
from loan_recommendation.agent_commands.schemas import AgentCommandCreate

# Must match main.py's static mount (repo root's static/, not backend/static/
# — main.py:_ROOT is one level above backend/, so this needs one more
# dirname() than a same-depth file under backend/ would use).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

UPLOAD_FOLDER = os.path.join(REPO_ROOT, "static", "uploads", "requirements")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_ATTACHMENT_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx",
    "png", "jpg", "jpeg", "webp", "txt", "csv",
}


def save_attachment(file: UploadFile | None) -> tuple[str | None, str | None]:
    """Returns (stored_filename, original_filename), or (None, None) if no file was given."""

    if file is None or not file.filename:
        return None, None

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported attachment file type.")

    stored_filename = f"{uuid.uuid4()}.{extension}"

    file_path = os.path.join(UPLOAD_FOLDER, stored_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return stored_filename, file.filename


def serialize_command(command: AgentCommand) -> dict:
    return {
        "id": command.id,
        "scenario": command.scenario,
        "instruction": command.instruction,
        "loan_types": [t for t in (command.loan_type or "").split(",") if t],
        "bank_id": command.bank_id,
        "attachment_filename": command.attachment_original_name,
        # Served via a dedicated download route (routes.py), not the shared
        # /static Mount — that Mount 404s whenever ROOT_PATH is set (e.g.
        # behind the nginx /api/ proxy in production), a pre-existing issue
        # unrelated to this feature that also affects company logo uploads.
        "attachment_url": (
            f"/agent-commands/{command.id}/attachment"
            if command.attachment_filename else None
        ),
        "created_at": command.created_at,
        "updated_at": command.updated_at,
    }


def list_global_commands(
    db: Session
):

    return (
        db.query(AgentCommand)
        .filter(
            AgentCommand.bank_id.is_(None)
        )
        .order_by(
            AgentCommand.created_at
        )
        .all()
    )


def list_bank_commands(
    db: Session,
    bank_id: int
):

    return (
        db.query(AgentCommand)
        .filter(
            AgentCommand.bank_id == bank_id
        )
        .order_by(
            AgentCommand.created_at
        )
        .all()
    )


def create_command(
    db: Session,
    command: AgentCommandCreate,
    bank_id: int | None = None,
    attachment_filename: str | None = None,
    attachment_original_name: str | None = None,
):

    new_command = AgentCommand(
        scenario=command.scenario,
        instruction=command.instruction,
        loan_type=",".join(command.loan_types) if command.loan_types else None,
        bank_id=bank_id,
        attachment_filename=attachment_filename,
        attachment_original_name=attachment_original_name,
    )

    db.add(new_command)

    db.commit()

    db.refresh(new_command)

    return new_command


def get_command(
    db: Session,
    command_id: int
):

    return (
        db.query(AgentCommand)
        .filter(
            AgentCommand.id == command_id
        )
        .first()
    )


def update_command(
    db: Session,
    command: AgentCommand,
    data: AgentCommandCreate,
    attachment_filename: str | None = None,
    attachment_original_name: str | None = None,
    remove_attachment: bool = False,
):

    command.scenario = data.scenario

    command.instruction = data.instruction

    command.loan_type = ",".join(data.loan_types) if data.loan_types else None

    if attachment_filename:
        _delete_attachment_file(command.attachment_filename)
        command.attachment_filename = attachment_filename
        command.attachment_original_name = attachment_original_name
    elif remove_attachment:
        _delete_attachment_file(command.attachment_filename)
        command.attachment_filename = None
        command.attachment_original_name = None

    db.commit()

    db.refresh(command)

    return command


def delete_command(
    db: Session,
    command: AgentCommand
):

    _delete_attachment_file(command.attachment_filename)

    db.delete(command)

    db.commit()


def _delete_attachment_file(stored_filename: str | None):
    if not stored_filename:
        return
    file_path = os.path.join(UPLOAD_FOLDER, stored_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
