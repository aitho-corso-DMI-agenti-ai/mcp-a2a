"""Utility functions"""

from typing import List
from langchain_core.documents import Document
from langchain_core.documents.base import Blob

from urllib.parse import unquote
from bs4 import BeautifulSoup
import requests

def get_coordinates(city_name: str):
    """
    Ottiene latitudine e longitudine da una località usando l'API di geocodifica di Open-Meteo.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city_name,
        "count": 1,
        "language": "it",
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            result = data["results"][0]
            return result["latitude"], result["longitude"], result.get("timezone", "Europe/Rome")

        return None, None, None
    except requests.RequestException as e:
        print("Errore nella geocodifica:", e)
        return None, None, None

def decode_weather_code(code: int) -> str:
    """Decodifica il codice meteo in una stringa di condizione."""

    code_map = {
        0: "clear_sky",
        1: "mainly_clear",
        2: "partly_cloudy",
        3: "overcast",
        45: "fog",
        48: "depositing_rime_fog",
        51: "light_drizzle",
        53: "moderate_drizzle",
        55: "dense_drizzle",
        56: "light_freezing_drizzle",
        57: "dense_freezing_drizzle",
        61: "slight_rain",
        63: "moderate_rain",
        65: "heavy_rain",
        66: "light_freezing_rain",
        67: "heavy_freezing_rain",
        71: "slight_snow_fall",
        73: "moderate_snow_fall",
        75: "heavy_snow_fall",
        77: "snow_grains",
        80: "slight_rain_showers",
        81: "moderate_rain_showers",
        82: "violent_rain_showers",
        85: "slight_snow_showers",
        86: "heavy_snow_showers",
        95: "thunderstorm",
        96: "thunderstorm_with_slight_hail",
        99: "thunderstorm_with_heavy_hail"
    }

    return code_map.get(code, "unknown_condition")

def get_web_page_content(encoded_url: str) -> str:
    """
    Recupera il contenuto testuale di una pagina web (titolo + testo principale).
    L'URL è codificato per l'uso in URI.
    """
    url = unquote(encoded_url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Errore nel recupero della pagina: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Prendiamo il titolo + primi paragrafi come esempio di estratto utile
    title = soup.title.string.strip() if soup.title else "Nessun titolo"
    paragraphs = soup.find_all("p")
    text = "\n".join(p.get_text(strip=True) for p in paragraphs[:3])

    return f"Titolo: {title}\n\nEstratto:\n{text}"


def convert_blobs_to_documents(blobs: List[Blob]) -> List[Document]:
    """
    Converte una lista di Blob in Documenti Langchain.
    Ogni Blob viene convertito in un oggetto Document con il suo contenuto e metadati.
    """
    docs = []
    for blob in blobs:
        blob_uri = str(blob.metadata.get("uri"))

        document = Document(
            page_content=blob.data,
            metadata={
                "source": blob.metadata.get("uri"),
                "mimetype": blob.mimetype,
            }
        )
        docs.append(document)
        print(f"Blob with MCP source `{blob_uri}` converted to Document.")
    return docs
