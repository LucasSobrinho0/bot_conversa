import os
import requests
from dotenv import load_dotenv

BASE_URL = "https://backend.botconversa.com.br/api/v1/webhook"
REQUEST_TIMEOUT = 30


def get_api_key() -> str:
    load_dotenv()
    api_key = (os.getenv("API_KEY") or "").strip()
    if not api_key:
        raise ValueError("API_KEY nao encontrada. Defina no .env ou na variavel de ambiente.")
    return api_key


def list_flows(api_key: str) -> list[dict]:
    url = f"{BASE_URL}/flows/"
    headers = {
        "API-KEY": api_key,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code >= 400:
        details = response.text.strip()
        raise RuntimeError(f"Falha ao listar flows ({response.status_code}): {details}")

    if not response.content:
        return []

    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Resposta inesperada da API: {data}")

    return data


def main() -> None:
    api_key = get_api_key()
    flows = list_flows(api_key)

    if not flows:
        print("Nenhum flow encontrado.")
        return

    print("id\tname")
    for flow in sorted(flows, key=lambda item: str(item.get("name", "")).lower()):
        flow_id = flow.get("id", "")
        name = flow.get("name", "")
        print(f"{flow_id}\t{name}")


if __name__ == "__main__":
    main()
