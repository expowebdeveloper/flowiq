import math


class EMIService:

    def calculate_emi(
        self,
        loan_amount,
        annual_interest_rate,
        tenure_years
    ):

        monthly_interest_rate = annual_interest_rate / (12 * 100)

        number_of_months = tenure_years * 12

        emi = (
            loan_amount
            * monthly_interest_rate
            * math.pow(1 + monthly_interest_rate, number_of_months)
        ) / (
            math.pow(1 + monthly_interest_rate, number_of_months) - 1
        )

        total_payment = emi * number_of_months

        total_interest = total_payment - loan_amount

        return {
            "monthly_emi": round(emi, 2),
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_payment, 2)
        }