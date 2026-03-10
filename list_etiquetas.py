import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["API_KEY"]
url = "https://backend.botconversa.com.br/api/v1/webhook/tags/"

resp = requests.get(url, headers={"API-KEY": API_KEY})
resp.raise_for_status()

for tag in resp.json():
    print(f"{tag['id']} - {tag['name']}")
