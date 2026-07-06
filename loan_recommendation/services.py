import json
from loan_recommendation.ai_service import AIService
from loan_recommendation.emi_service import EMIService

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

    def get_eligible_banks(self, request):
        """
        Returns all banks for which the customer is eligible.
        """

        with open("loan_recommendation/banks.json", "r") as file:
            banks = json.load(file)

        eligible_banks = []

        for bank in banks:

            # Loan type check
            if request.loan_type.lower() != bank["loan_product"].lower():
                continue

            # Credit score check
            if request.credit_score < bank["min_credit_score"]:
                continue

            # Monthly income check
            if request.monthly_income < bank["min_monthly_income"]:
                continue

            # Maximum loan amount check
            if request.loan_amount > bank["max_loan_amount"]:
                continue

            # Loan-to-Value (LTV) check
            ltv = (request.loan_amount / request.property_value) * 100

            if ltv > bank["max_ltv"]:
                continue

            # Age Check
            if request.age < bank["min_age"] or request.age > bank["max_age"]:
                continue

            # Employment Type Check
            if request.employment_type not in bank["employment_types"]:
                continue

            # Work Experience Check
            if request.work_experience_years < bank["minimum_work_experience_years"]:
                continue

            # Property Type Check
            if request.property_type not in bank["property_types"]:
                continue


            # FOIR Check
            foir = (request.existing_emi / request.monthly_income) * 100

            if foir > bank["maximum_foir"]:
                continue

            # Customer is eligible
            eligible_banks.append(bank)

        return eligible_banks


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

    def recommend(self, request):

        print("1. Validation")
        self.validation_service.validate(request)

        print("2. Eligibility")
        eligible_banks = self.eligibility_service.get_eligible_banks(request)

        print("3. Ranking")
        ranked_banks = self.ranking_service.rank_banks(
            eligible_banks,
            request
        )

        # Top 5 Banks
        top_banks = ranked_banks[:5]

        print("4. Calculating EMI")

        for bank in top_banks:

            emi = self.emi_service.calculate_emi(
                loan_amount=request.loan_amount,
                annual_interest_rate=bank["interest_rate"],
                tenure_years=bank["max_tenure"]
            )

            bank.update(emi)

        print("5. Calling AI")

        ai_response = self.ai_service.generate_explanation(
            request,
            top_banks
        )

        print("6. AI Returned")

        final_response = self.ai_service.merge_ai_response(
            top_banks,
            ai_response
        )

        print("7. Merge Completed")

        return final_response