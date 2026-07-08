import json
from loan_recommendation.ai_service import AIService
from loan_recommendation.emi_service import EMIService
from loan_recommendation.crud import (
    get_saved_recommendation,
    save_recommendation,
    get_eligible_banks
)

class ValidationService:

    def validate(self, request):

        if not request.customer_name.strip():
            raise ValueError("Customer name is required.")

        if request.monthly_income <= 0:
            raise ValueError("Monthly income must be greater than 0.")

        if request.credit_score < 300 or request.credit_score > 900:
            raise ValueError("Credit score must be between 300 and 900.")

        if request.loan_amount <= 0:
            raise ValueError("Loan amount must be greater than 0.")

        if request.property_value <= 0:
            raise ValueError("Property value must be greater than 0.")

        if request.existing_emi < 0:
            raise ValueError("Existing EMI cannot be negative.")

        if not request.loan_type.strip():
            raise ValueError("Loan type is required.")
        
        # Age Validation
        if request.age < 18:
            raise ValueError("Customer must be at least 18 years old.")

        # Employment Type Validation
        if not request.employment_type.strip():
            raise ValueError("Employment type is required.")

        # Work Experience Validation
        if request.work_experience_years < 0:
            raise ValueError("Work experience cannot be negative.")

        # Property Type Validation
        if not request.property_type.strip():
            raise ValueError("Property type is required.")
        
        

        return True
    


class EligibilityService:

    def get_eligible_banks(self, db, request):
        """
        Returns all banks for which the customer is eligible.
        """

        banks = get_eligible_banks(
            db=db,
            loan_type=request.loan_type,
            cibil=request.credit_score,
            income=request.monthly_income,
            loan_amount=request.loan_amount
        )

        print("=" * 80)
        print(f"Total banks fetched from database: {len(banks)}")
        print(banks)
        print("=" * 80)

        eligible_banks = []
        rejected_banks = []

        print("=" * 80)
        print("REQUEST VALUES")
        print("Property Type:", repr(request.property_type))
        print("Employment Type:", repr(request.employment_type))
        print("Loan Type:", repr(request.loan_type))
        print("=" * 80)
        for bank in banks:
            print(f"\nChecking Bank: {bank['bank_name']}")
            reasons = []

            # Loan type check
            if request.loan_type.lower() != bank["loan_product"].lower():
                print("❌ Loan Type Failed")
                continue

            # Credit score check
            if request.credit_score < bank["min_credit_score"]:

                print("❌ Credit Score Failed")

                reasons.append(
                    f"Minimum credit score required is {bank['min_credit_score']}. "
                    f"Your score is {request.credit_score}."
                )

            if request.monthly_income < bank["min_monthly_income"]:

                print("❌ Monthly Income Failed")

                reasons.append(
                    f"Minimum monthly income required is ₹{bank['min_monthly_income']:,.0f}. "
                    f"Your income is ₹{request.monthly_income:,.0f}."
                )

            # Maximum loan amount check
            if request.loan_amount > bank["max_loan_amount"]:

                print("❌ Loan Amount Failed")

                reasons.append(
                    f"Maximum loan amount is ₹{bank['max_loan_amount']:,.0f}. "
                    f"You requested ₹{request.loan_amount:,.0f}."
                )

            # Loan-to-Value (LTV) check
            ltv = (request.loan_amount / request.property_value) * 100

            if ltv > bank["max_ltv"]:

                print("❌ LTV Failed")

                reasons.append(
                    f"Loan-to-Value (LTV) is {ltv:.2f}%. "
                    f"Maximum allowed is {bank['max_ltv']}%."
                )

            # Age Check
            if request.age < bank["min_age"] or request.age > bank["max_age"]:

                print("❌ Age Failed")

                reasons.append(
                    f"Eligible age is {bank['min_age']} to {bank['max_age']} years. "
                    f"Your age is {request.age} years."
                )

            # Employment Type Check
            if request.employment_type not in bank["employment_types"]:

                print("❌ Employment Type Failed")

                reasons.append(
                    f"This bank accepts only {', '.join(bank['employment_types'])}. "
                    f"You selected '{request.employment_type}'."
                )

            # Work Experience Check
            if request.work_experience_years < bank["minimum_work_experience_years"]:

                print("❌ Work Experience Failed")

                reasons.append(
                    f"Minimum work experience required is "
                    f"{bank['minimum_work_experience_years']} years. "
                    f"You have {request.work_experience_years} years."
                )

            # Property Type Check
            print("User Property Type :", repr(request.property_type))
            print("Bank Property Types:", bank["property_types"])
            if request.property_type not in bank["property_types"]:

                print("❌ Property Type Failed")

                reasons.append(
                    f"This bank supports only "
                    f"{', '.join(bank['property_types'])}. "
                    f"You selected '{request.property_type}'."
                )


            # FOIR Check
            foir = (request.existing_emi / request.monthly_income) * 100

            if foir > bank["maximum_foir"]:

                print("❌ FOIR Failed")

                reasons.append(
                    f"FOIR is {foir:.2f}%. "
                    f"Maximum allowed is {bank['maximum_foir']}%."
                )

            if reasons:

                rejected_banks.append({
                    "bank_name": bank["bank_name"],
                    "reasons": reasons
                })

                continue
            # Customer is eligible
            print("✅ Eligible")
            eligible_banks.append(bank)

        return {
            "eligible_banks": eligible_banks,
            "rejected_banks": rejected_banks
        }


class RankingService:

    def rank_banks(self, eligible_banks, request):

        ranked_banks = []

        for bank in eligible_banks:

            score = 0

            # Lower interest rate is better
            score += (10 - bank["interest_rate"]) * 10

            # Longer tenure is better
            score += bank["max_tenure"]

            # Lower processing fee is better
            score += max(0, 10 - (bank["processing_fee"] / 1000))

            # Better credit score match
            score += (request.credit_score - bank["min_credit_score"]) / 10

            # Better income match
            score += (
                request.monthly_income
                - bank["min_monthly_income"]
            ) / 10000

            bank["score"] = round(score, 2)

            ranked_banks.append(bank)

        ranked_banks.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return ranked_banks



class RecommendationService:

    def __init__(self):
        self.validation_service = ValidationService()
        self.eligibility_service = EligibilityService()
        self.ranking_service = RankingService()
        self.ai_service = AIService()
        self.emi_service = EMIService()

    def recommend(self, db, request):

        self.validation_service.validate(request)
        saved = None

        # saved = get_saved_recommendation(
        #     db,
        #     request
        # )

        # if saved:

        #     print("Recommendation loaded from database.")

        #     return json.loads(saved.response)

        eligibility_result = self.eligibility_service.get_eligible_banks(
            db,
            request
        )

        eligible_banks = eligibility_result["eligible_banks"]

        rejected_banks = eligibility_result["rejected_banks"]

        ranked_banks = self.ranking_service.rank_banks(
            eligible_banks,
            request
        )

        if not eligible_banks:

            return {
                "recommendations": [],
                "rejected_banks": rejected_banks
            }

        # Top 5 Banks
        top_banks = ranked_banks[:5]

        print("=" * 80)
        print("TOP BANKS")
        print(top_banks)
        print("=" * 80)


        for bank in top_banks:

            print("=" * 80)
            print("Calculating EMI for:", bank["bank_name"])

            emi = self.emi_service.calculate_emi(
                loan_amount=request.loan_amount,
                annual_interest_rate=bank["interest_rate"],
                tenure_years=bank["max_tenure"]
            )

            print("EMI Result:", emi)

            bank.update(emi)


        try:

            ai_response = self.ai_service.generate_explanation(
                request,
                top_banks
            )

        except Exception as e:

            print(f"AI Error: {e}")

            ai_response = {
                "recommendations": [
                    {
                        "bank_name": bank["bank_name"],
                        "approval_probability": "Unknown",
                        "reason": "AI explanation unavailable.",
                        "advantages": [],
                        "disadvantages": []
                    }
                    for bank in top_banks
                ]
            }

        final_response = self.ai_service.merge_ai_response(
            top_banks,
            ai_response
        )

        save_recommendation(
            db,
            request,
            final_response
        )

        print("=" * 80)
        print("FINAL RESPONSE")
        print(final_response)
        print("=" * 80)

        return {
            "recommendations": final_response,
            "rejected_banks": rejected_banks
        }