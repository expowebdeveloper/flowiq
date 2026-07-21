from sqlalchemy.orm import Session

from loan_recommendation.agent_commands.crud import (
    list_global_commands,
    list_bank_commands,
    create_command,
    get_command,
    update_command,
    delete_command
)

from loan_recommendation.agent_commands.schemas import (
    AgentCommandCreate
)


class AgentCommandService:

    def list_global_commands(
        self,
        db: Session
    ):

        return list_global_commands(db=db)

    def list_bank_commands(
        self,
        db: Session,
        bank_id: int
    ):

        return list_bank_commands(db=db, bank_id=bank_id)

    def create_command(
        self,
        db: Session,
        command: AgentCommandCreate,
        bank_id: int | None = None,
        attachment_filename: str | None = None,
        attachment_original_name: str | None = None,
    ):

        return create_command(
            db=db,
            command=command,
            bank_id=bank_id,
            attachment_filename=attachment_filename,
            attachment_original_name=attachment_original_name,
        )

    def get_command(
        self,
        db: Session,
        command_id: int
    ):

        return get_command(db=db, command_id=command_id)

    def update_command(
        self,
        db: Session,
        command,
        data: AgentCommandCreate,
        attachment_filename: str | None = None,
        attachment_original_name: str | None = None,
        remove_attachment: bool = False,
    ):

        return update_command(
            db=db,
            command=command,
            data=data,
            attachment_filename=attachment_filename,
            attachment_original_name=attachment_original_name,
            remove_attachment=remove_attachment,
        )

    def delete_command(
        self,
        db: Session,
        command
    ):

        return delete_command(db=db, command=command)
