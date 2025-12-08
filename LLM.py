import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Constants
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 300
DEFAULT_TOP_P = 1
REQUEST_TIMEOUT = 30
MIN_TEXT_LENGTH = 3
MAX_TEXT_LENGTH = 5000

PROMPT_TEMPLATE = (
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
    "{query}\n"
    "---END INPUT---\n\n"
    "Formatuokite atsakymą kaip:\n"
    "- Patiekalas: [name]"
)

ERROR_EMPTY_QUERY = "Prašome įvesti tinkamą patiekalą."
ERROR_NO_DISHES = "Maisto produktų nerasta."
ERROR_NO_API_RESPONSE = "Negauta atsakymo iš API"
ERROR_TRANSCRIPTION_EMPTY = "Klaida: transkribuotas tekstas tuščias arba neteisingas."
DISH_MARKER = "Patiekalas:"


class LLMClient:
    """
    Klasė, apjungianti visus LLM susijusius metodus,
    kurie anksčiau buvo modulio lygio funkcijos.
    """

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url

    def call_llama_api(self, query: str) -> dict:
        """Call Llama API for food extraction"""
        validation_error = self._validate_query(query)
        if validation_error:
            return {"error": validation_error}

        try:
            response = self._make_api_request(query)
            return self._parse_api_response(response)
        except requests.exceptions.RequestException as e:
            return {"error": f"Klaida jungiantis: {str(e)}"}
        except Exception as e:
            return {"error": f"Klaida, jungiantis prie API: {str(e)}"}

    def _validate_query(self, query: str) -> str | None:
        """Validate query input"""
        if not query or not query.strip():
            return ERROR_EMPTY_QUERY
        return None

    def _make_api_request(self, query: str) -> requests.Response:
        """Make HTTP request to API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": DEFAULT_MODEL,
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(query=query)}],
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "top_p": DEFAULT_TOP_P
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            data=json.dumps(data),
            verify=False,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()
        return response

    def _parse_api_response(self, response: requests.Response) -> dict:
        """Parse API response and extract content"""
        result = response.json()

        content = self._extract_content_from_result(result)
        
        if content is None:
            return {"error": ERROR_NO_API_RESPONSE}
        
        if self._is_content_invalid(content):
            print(ERROR_TRANSCRIPTION_EMPTY)
            return {"text": ERROR_NO_DISHES}
        
        return {"text": content}

    def _extract_content_from_result(self, result: dict) -> str | None:
        """Extract content from API result"""
        if "choices" not in result:
            return None
        
        choices = result["choices"]
        if len(choices) == 0:
            return None
        
        if "message" not in choices[0]:
            return None
        
        message = choices[0]["message"]
        if "content" not in message:
            return None
        
        return message["content"]

    def _is_content_invalid(self, content: str) -> bool:
        """Check if content is invalid or empty"""
        if not content.strip() or content.strip() == "None":
            return True
        
        if DISH_MARKER not in content:
            return True
        
        return False

    def process_response(self, response: dict) -> str:
        """Process API response (anksčiau ProcessResponse)."""
        if "error" in response:
            return response["error"]

        result = response.get("text", "Negauta atsakymo")

        if not result.strip() or result.strip() == "None" or DISH_MARKER not in result:
            print(ERROR_TRANSCRIPTION_EMPTY)
            return ERROR_NO_DISHES

        dishes = result.split("\n")
        formatted_output = "Aptikti patiekalai:\n" + "\n".join(dishes)
        return formatted_output

    def send_query(self, query: str) -> str:
        """
        Send query to LLM (anksčiau modulio funkcija send_query)
        """
        if not query.strip():
            return ERROR_EMPTY_QUERY

        response = self.call_llama_api(query)
        return self.process_response(response)

    def validate_input(
        self,
        text: str,
        min_length: int = MIN_TEXT_LENGTH,
        max_length: int = MAX_TEXT_LENGTH
    ) -> tuple[bool, str]:
        """
        Validate input text (anksčiau ValidateInput)
        """
        if not text or not text.strip():
            return False, ERROR_EMPTY_QUERY

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
            if DISH_MARKER in line:
                dish = line.replace(f"{DISH_MARKER}", "").strip()
                dish = dish.replace("- ", "")
                dishes.append(dish)

        return dishes

    def format_dishes_output(self, dishes: list[str]) -> str:
        """
        Format dishes for display
        """
        if len(dishes) == 0:
            return ERROR_NO_DISHES

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
            return None