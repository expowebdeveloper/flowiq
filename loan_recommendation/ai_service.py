import json
from ollama import chat


class AIService:

    def load_prompt(self):

        with open(
            "loan_recommendation/recommendation_prompt.txt",
            "r",
            encoding="utf-8"
        ) as file:
            return file.read()


    def build_prompt(self, customer, recommendations):

        prompt = self.load_prompt()

        customer_data = json.dumps(
            customer.model_dump(),
            indent=4
        )

        clean_recommendations = []

        for bank in recommendations:

            clean_recommendations.append(
                {
                    "bank_name": bank["bank_name"],
                    "loan_product": bank["loan_product"],
                    "interest_rate": bank["interest_rate"],
                    "processing_fee": bank["processing_fee"],
                    "max_tenure": bank["max_tenure"],
                    "required_documents": bank["required_documents"],
                    "score": bank["score"]
                }
            )

        recommendation_data = json.dumps(
            clean_recommendations,
            indent=4
        )

        return f"""
    {prompt}

    Customer Profile

    {customer_data}

    Recommended Banks

    {recommendation_data}
    """

    
    def generate_explanation(self, customer, recommendations):

        prompt = self.build_prompt(
            customer,
            recommendations
        )

        print("Calling Ollama...")
        import time
        
        start = time.time()

        response = chat(
            model="phi3:mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        end = time.time()

        print(f"AI took {end - start:.2f} seconds")

        content = response["message"]["content"]

        print(content)

        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

        return json.loads(content)

    def merge_ai_response(self, recommendations, ai_response):

        ai_recommendations = ai_response.get("recommendations", [])

        ai_lookup = {
            item["bank_name"]: item
            for item in ai_recommendations
        }

        merged = []

        for bank in recommendations:

            ai_data = ai_lookup.get(bank["bank_name"], {})

            bank["approval_probability"] = ai_data.get(
                "approval_probability",
                "Unknown"
            )

            bank["reason"] = ai_data.get(
                "reason",
                ""
            )

            bank["advantages"] = ai_data.get(
                "advantages",
                []
            )

            bank["disadvantages"] = ai_data.get(
                "disadvantages",
                []
            )

            merged.append(bank)

        return merged