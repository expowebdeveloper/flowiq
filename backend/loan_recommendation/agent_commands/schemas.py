from pydantic import BaseModel


class AgentCommandCreate(BaseModel):

    scenario: str

    instruction: str

    # Empty/omitted = applies to every loan type; otherwise one or more of
    # the canonical loan_type values (home_loan, education_loan, ...).
    # Stored in the DB as a comma-joined string in the same loan_type
    # column, converted to/from a list at this API boundary.
    loan_types: list[str] = []
