import json
from ollama import chat
import requests

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

        print("=" * 80)
        print("PROMPT LENGTH:", len(prompt))
        print("=" * 80)
        
        last_error = None

        for attempt in range(3):
            import time

            print("=" * 80)
            print("Calling Ollama...")
            start = time.time()

            print(prompt)
            print("=" * 100)

            response = requests.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": "phi3:mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False
                },
                timeout=120
            )

            response.raise_for_status()

            content = response.json()["message"]["content"]

            content = (
                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            print(f"\nAttempt {attempt + 1}")
            print("=" * 80)
            print(content)
            print("=" * 80)

            try:
                return json.loads(content)

            except json.JSONDecodeError as e:
                last_error = e
                print(f"Invalid JSON. Retrying... ({attempt + 1}/3)")

        raise ValueError(
            f"AI returned invalid JSON after 3 attempts.\n{last_error}"
        )

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