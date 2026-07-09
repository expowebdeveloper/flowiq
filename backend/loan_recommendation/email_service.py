class EmailService:

    def generate_email_body(self, customer, recommendations):

        body = f"""
Dear {customer.customer_name},

Based on the information you provided, here are your recommended loan options.

"""

        for index, bank in enumerate(recommendations, start=1):

            body += f"""
--------------------------------------------------

Recommendation {index}

Bank Name: {bank["bank_name"]}

Loan Product: {bank["loan_product"]}

Interest Rate: {bank["interest_rate"]}%

Processing Fee: ₹{bank["processing_fee"]}

Maximum Tenure: {bank["max_tenure"]} Years

Approval Probability: {bank["approval_probability"]}

Reason:
{bank["reason"]}

Advantages:
"""

            for advantage in bank["advantages"]:
                body += f"\n- {advantage}"

            body += "\n\nDisadvantages:\n"

            for disadvantage in bank["disadvantages"]:
                body += f"- {disadvantage}\n"

            body += "\nRequired Documents:\n"

            for document in bank["required_documents"]:
                body += f"- {document}\n"

        body += """

--------------------------------------------------

Thank you for choosing FlowIQ.

Regards,
FlowIQ Team
"""

        return body

    def send_email(self, recipient_email, subject, body):
        pass