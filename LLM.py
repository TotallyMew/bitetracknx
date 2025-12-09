import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMClient:
    """
    Klasė, apjungianti visus LLM susijusius metodus,
    kurie anksčiau buvo modulio lygio funkcijos.
    """

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url

    def call_llama_api(self, query: str) -> dict:
        """
        Call Llama API for food extraction
        """
        if not query:
            return {"error": "Prašome įvesti tinkamą patiekalą."}

        if not query.strip():
            return {"error": "Prašome įvesti tinkamą patiekalą."}

        prompt = (
            "Pavyzdys:\n"
            "---EXAMPLE---\n"
            "Šiandien vakare valgiau kebabą su česnakiniu padažu. "
            "Ryte, atsikėlęs valgiau cepelinus su kiauliena.\n"
            "Atsakymas turėtų būti:\n"
            "- Patiekalas: Kebabas su česnakiniu padažu\n"
            "- Patiekalas: Cepelinai su kiauliena\n"
            "---END EXAMPLE---\n\n"
            "Patvarkyk rašybos klaidas, žodžių galūnes, kad būtų lietuviškos.\n"
            "Išrink tik maisto produktus ir sudaryk patiekalus iš toliau pateikto "
            "teksto aprašymo, kuris pateikiamas lietuvių kalba. "
            "Jei nebuvo pateikta maisto patiekalų, neatsakyk į žinutę.\n"
            "Surašykite juos atskirai nuorodų formatu:\n\n"
            "---INPUT---\n"
            f"{query}\n"
            "---END INPUT---\n\n"
            "Formatuokite atsakymą kaip:\n"
            "- Patiekalas: [name]"
        )

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 1
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(data),
                verify=False,
                timeout=30
            )

            response.raise_for_status()

            result = response.json()

            if "choices" in result:
                choices = result["choices"]
                if len(choices) > 0:
                    if "message" in choices[0]:
                        message = choices[0]["message"]
                        if "content" in message:
                            content = message["content"]

                            if not content.strip() or content.strip() == "None":
                                print("Klaida: transkribuotas tekstas tuščias arba neteisingas.")
                                return {"text": "Maisto produktų nerasta."}

                            if "Patiekalas:" not in content:
                                print("Klaida: transkribuotas tekstas tuščias arba neteisingas.")
                                return {"text": "Maisto produktų nerasta."}

                            return {"text": content}

            return {"error": "Negauta atsakymo iš API"}

        except requests.exceptions.RequestException as e:
            return {"error": f"Klaida jungiantis: {str(e)}"}
        except Exception as e:
            return {"error": f"Klaida, jungiantis prie API: {str(e)}"}

    def process_response(self, response: dict) -> str:
        """Process API response (anksčiau ProcessResponse)."""
        if "error" in response:
            return response["error"]

        result = response.get("text", "Negauta atsakymo")

        if not result.strip() or result.strip() == "None" or "Patiekalas:" not in result:
            print("Klaida: transkribuotas tekstas tuščias arba neteisingas.")
            return "Maisto produktų nerasta."

        dishes = result.split("\n")
        formatted_output = "Aptikti patiekalai:\n" + "\n".join(dishes)
        return formatted_output

    def send_query(self, query: str) -> str:
        """
        Send query to LLM (anksčiau modulio funkcija send_query)
        """
        if not query.strip():
            return "Prašome įvesti tinkamą patiekalą."

        response = self.call_llama_api(query)
        return self.process_response(response)

    def validate_input(
        self,
        text: str,
        min_length: int = 3,
        max_length: int = 5000
    ) -> tuple[bool, str]:
        """
        Validate input text (anksčiau ValidateInput)
        """
        if not text:
            return False, "Prašome įvesti tinkamą patiekalą."

        if not text.strip():
            return False, "Prašome įvesti tinkamą patiekalą."

        if len(text) < min_length:
            return False, "Tekstas per trumpas"

        if len(text) > max_length:
            return False, "Tekstas per ilgas"

        return True, "OK"

    def extract_dishes(self, text: str) -> list[str]:
        """
        Extract dishes from LLM response
        """
        lines = text.split("\n")
        dishes: list[str] = []

        for line in lines:
            if "Patiekalas:" in line:
                dish = line.replace("Patiekalas:", "").strip()
                dish = dish.replace("- ", "")
                dishes.append(dish)

        return dishes

    def format_dishes_output(self, dishes: list[str]) -> str:
        """
        Format dishes for display
        """
        if len(dishes) == 0:
            return "Maisto produktų nerasta."

        output = "Aptikti patiekalai:\n"
        for i, dish in enumerate(dishes, 1):
            output += f"{i}. {dish}\n"
        return output

    def safe_api_call(self, query: str) -> dict | None:
        """
        Call API with error suppression
        """
        try:
            return self.call_llama_api(query)
        except Exception:
            # specialiai nieko nedarom – kaip ir senajame variante
            return None