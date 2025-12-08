import os
import json
import requests


API_KEY = "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"
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_llama_api(query):
    try:
        # Prompt for extracting food items.
        prompt = (
            "Pavyzdys:\n"
            "---EXAMPLE---\n"
            "Šiandien vakare valgiau kebabą su česnakiniu padažu. Ryte, atsikėlęs valgiau cepelinus su kiauliena.\n"
            "Atsakymas turėtų būti:\n"
            "- Patiekalas: Kebabas su česnakiniu padažu\n"
            "- Patiekalas: Cepelinai su kiauliena\n"
            "---END EXAMPLE---\n\n"
            "Patvarkyk rašybos klaidas, žodžių galūnes, kad būtų lietuviškos.\n"
            "Išrink tik maisto produktus ir sudaryk patiekalus iš toliau pateikto teksto aprašymo, kuris pateikiamas lietuvių kalba. Jei nebuvo pateikta maisto patiekalų, neatsakyk į žinutę.\n"
            "Surašykite juos atskirai nuorodų formatu:\n\n"
            "---INPUT---\n"
            f"{query}\n"
            "---END INPUT---\n\n"
            "Formatuokite atsakymą kaip:\n"
            "- Patiekalas: [name]"
        )

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 1
        }

        # Send API request
        response = requests.post(BASE_URL, headers=headers, data=json.dumps(data), verify=False)
        response.raise_for_status()

        # Extract response text
        result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": result}

    except requests.exceptions.RequestException as e:
        return {"error": f"Klaida jungiantis: {str(e)}"}
    except Exception as e:
        return {"error": f"Klaida, jungiantis prie API: {str(e)}"}


def process_response(response):
    if "error" in response:
        return response["error"]

    result = response.get("text", "Negauta atsakymo")

    # tikrinam ar tuscias ats ir nera maisto patiekalu
    if not result.strip() or result.strip() == "None" or "Patiekalas:" not in result:
        print("Klaida: transkribuotas tekstas tuščias arba neteisingas.")
        return "Maisto produktų nerasta."

    # Process and format the dishes
    dishes = result.split("\n")
    formatted_output = "Aptikti patiekalai:\n" + "\n".join(dishes)
    return formatted_output


def send_query(query):
    if not query.strip():
        return "Prašome įvesti tinkamą patiekalą."

    response = call_llama_api(query)
    return process_response(response)
