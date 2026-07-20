import requests


def get_wikipedia_information(company_name: str):

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{company_name}"

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent": "FlowIQ/1.0"
            },
            timeout=10
        )

        if response.status_code == 404:

            print(f"No Wikipedia page found for: {company_name}")

            return empty_result()

        if response.status_code != 200:

            print("Wikipedia API Error:", response.status_code)

            return empty_result()

        data = response.json()

        return {

            "description": data.get("extract"),

            "industry": None,

            "founded": None,

            "headquarters": None,

            "founders": None,

            "employees": None,

            "logo": None

        }

    except Exception as e:

        print("Wikipedia Exception:", e)

        return empty_result()


def empty_result():

    return {

        "description": None,

        "industry": None,

        "founded": None,

        "headquarters": None,

        "founders": None,

        "employees": None,

        "logo": None

    }