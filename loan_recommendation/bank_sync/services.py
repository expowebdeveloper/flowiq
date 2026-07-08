import json

from db import SessionLocal

from loan_recommendation.crud import (
    get_bank_by_name,
    create_bank,
    create_bank_policy,
    get_bank_policy,
    update_bank_policy
)


def sync_banks():

    db = SessionLocal()

    with open("loan_recommendation/banks.json", "r") as file:
        banks = json.load(file)

    for bank_data in banks:

        bank = get_bank_by_name(
            db,
            bank_data["bank_name"]
        )

        if not bank:

            bank = create_bank(
                db=db,
                name=bank_data["bank_name"]
            )

        policy = get_bank_policy(
            db=db,
            bank_id=bank.id,
            loan_type=bank_data["loan_product"]
        )
        print(f"Bank: {bank.name}")
        print(f"Policy Found: {policy}")

        if policy:

            update_bank_policy(
                db=db,
                policy=policy,
                bank_data=bank_data
            )

        else:

            create_bank_policy(

                db=db,

                bank_id=bank.id,

                loan_type=bank_data["loan_product"],

                min_cibil=bank_data["min_credit_score"],

                max_cibil=900,

                min_income=bank_data["min_monthly_income"],

                max_loan_amount=bank_data["max_loan_amount"],

                interest_rate=bank_data["interest_rate"],

                processing_fee=bank_data["processing_fee"],

                max_ltv=bank_data["max_ltv"],

                min_age=bank_data["min_age"],

                max_age=bank_data["max_age"],

                minimum_work_experience_years=bank_data["minimum_work_experience_years"],

                maximum_foir=bank_data["maximum_foir"],

                employment_types=json.dumps(
                    bank_data["employment_types"]
                ),

                property_types=json.dumps(
                    bank_data["property_types"]
                ),

                required_documents=json.dumps(
                    bank_data["required_documents"]
                ),

                special_features=json.dumps(
                    bank_data["special_features"]
                ),

                prepayment_charges=bank_data["prepayment_charges"],

                foreclosure_charges=bank_data["foreclosure_charges"],

                min_tenure=1,

                max_tenure=bank_data["max_tenure"]

            )

    db.close()

    print("✅ Bank import completed successfully.")


if __name__ == "__main__":
    sync_banks()