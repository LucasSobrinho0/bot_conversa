import csv
import requests
from dotenv import load_dotenv
import os
from time import sleep
import random

load_dotenv()

BASE_URL = "https://backend.botconversa.com.br/api/v1/webhook"
REQUEST_TIMEOUT = 30
FLOW_ID = 8325072
FLOW_NAME = "Cold Zap (com audio)"

def _headers(api_key: str) -> dict:
    return {
        "API-KEY": api_key,
        "Content-Type": "application/json",
    }


def _normalize_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if phone.startswith("+"):
        return "+" + "".join(ch for ch in phone[1:] if ch.isdigit())
    return "".join(ch for ch in phone if ch.isdigit())


def read_csv(file_path: str = "contacts.csv") -> list[dict]:
    contacts = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(2048)
        file.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        except csv.Error:
            dialect = csv.excel

        reader = csv.reader(file, dialect=dialect)

        for row in reader:
            if not row:
                continue

            # Fallback para linhas com separador por espaco.
            if len(row) < 3:
                row = " ".join(row).split()
            if len(row) < 3:
                continue

            first_name = row[0].strip()
            last_name = row[1].strip()
            phone = _normalize_phone(row[2])

            if not phone:
                continue

            # Ignora cabecalho comum.
            if first_name.lower() in {"nome", "name", "first_name"} and phone.lower() in {
                "telefone",
                "phone",
            }:
                continue

            contacts.append(
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                }
            )

    return contacts


def find_contact(api_key: str, payload: dict) -> dict | None:
    phone = _normalize_phone(payload["phone"])
    url = f"{BASE_URL}/subscriber/get_by_phone/{phone}/"
    response = requests.get(url, headers=_headers(api_key), timeout=REQUEST_TIMEOUT)

    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        return None

    response.raise_for_status()
    return None


def create_contact(api_key: str, payload: dict) -> dict:
    url = f"{BASE_URL}/subscriber/"
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()

    if not first_name:
        first_name = "Contato"
    if not last_name:
        last_name = "SemSobrenome"

    body = {
        "phone": _normalize_phone(payload["phone"]),
        "first_name": first_name,
        "last_name": last_name,
        "has_opt_in_whatsapp": True,
    }

    response = requests.post(
        url,
        headers=_headers(api_key),
        json=body,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    if not response.content:
        return {}

    return response.json()


def send_message(api_key: str, payload: dict) -> dict:
    subscriber_id = payload["subscriber_id"]
    url = f"{BASE_URL}/subscriber/{subscriber_id}/send_message/"
    body = {
        "type": payload.get("type", "text"),
        "value": payload["value"],
    }

    response = requests.post(
        url,
        headers=_headers(api_key),
        json=body,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    if not response.content:
        return {}

    return response.json()


def list_flows(api_key: str) -> list[dict]:
    url = f"{BASE_URL}/flows/"
    response = requests.get(url, headers=_headers(api_key), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    if not response.content:
        return []

    return response.json()


def find_flow_id_by_name(api_key: str, flow_name: str) -> int:
    target_name = (flow_name or "").strip().lower()
    if not target_name:
        raise ValueError("Defina o nome do fluxo em FLOW_NAME.")

    flows = list_flows(api_key)
    matches = [flow for flow in flows if str(flow.get("name", "")).strip().lower() == target_name]

    if not matches:
        available = ", ".join(str(flow.get("name")) for flow in flows[:10]) or "nenhum fluxo encontrado"
        raise RuntimeError(f"Fluxo '{flow_name}' nao encontrado. Exemplos disponiveis: {available}")

    if len(matches) > 1:
        ids = ", ".join(str(flow.get("id")) for flow in matches)
        raise RuntimeError(f"Mais de um fluxo com nome '{flow_name}'. IDs encontrados: {ids}")

    flow_id = matches[0].get("id")
    if flow_id is None:
        raise RuntimeError(f"Fluxo '{flow_name}' sem ID retornado pela API.")

    return int(flow_id)


def send_flow(api_key: str, payload: dict) -> dict:
    subscriber_id = payload["subscriber_id"]
    url = f"{BASE_URL}/subscriber/{subscriber_id}/send_flow/"
    body = {"flow": int(payload["flow_id"])}

    response = requests.post(
        url,
        headers=_headers(api_key),
        json=body,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    if not response.content:
        return {}

    return response.json()


def get_or_create_subscriber_id(api_key: str, contact: dict) -> int:
    existing = find_contact(api_key, {"phone": contact["phone"]})
    if existing and existing.get("id"):
        return existing["id"]

    created = create_contact(api_key, contact)
    if created.get("id"):
        return created["id"]

    # Alguns endpoints nao retornam o objeto completo no create.
    existing_after_create = find_contact(api_key, {"phone": contact["phone"]})
    if existing_after_create and existing_after_create.get("id"):
        return existing_after_create["id"]

    raise RuntimeError(f"Nao foi possivel obter subscriber_id para {contact['phone']}")


if __name__ == "__main__":
    # Ajuste aqui com sua chave caso ainda nao tenha configurado no seu fluxo.
    api_key = os.getenv("API_KEY")

    if api_key in {"", "SUA_API_KEY_AQUI"}:
        raise ValueError("Defina sua API key real na variavel `api_key`.")

    if FLOW_ID is None and FLOW_NAME in {"", "NOME_DO_FLUXO"}:
        raise ValueError("Defina FLOW_ID ou FLOW_NAME antes de executar.")

    selected_flow_id = int(FLOW_ID) if FLOW_ID is not None else find_flow_id_by_name(api_key, FLOW_NAME)
    print(f"[INFO] Enviando fluxo ID {selected_flow_id}")

    contacts = read_csv("contacts.csv")

    for contact in contacts:
        try:
            random_seconds = random.randint(60, 360)
            sleep(random_seconds)
            subscriber_id = get_or_create_subscriber_id(api_key, contact)
            send_flow(
                api_key,
                {
                    "subscriber_id": subscriber_id,
                    "flow_id": selected_flow_id,
                },
            )
            print(f"[OK] Fluxo enviado para {contact['phone']} (subscriber_id={subscriber_id}) (nome={contact['first_name']})")
        except requests.HTTPError as exc:
            details = ""
            if exc.response is not None and exc.response.text:
                details = f" | resposta: {exc.response.text}"
            print(f"[ERRO] {contact['phone']}: {exc}{details}")
        except Exception as exc:
            print(f"[ERRO] {contact['phone']}: {exc}")

