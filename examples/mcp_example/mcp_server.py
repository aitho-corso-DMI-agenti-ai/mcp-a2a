"""MCP Server"""
import base64
import os
import wikipedia
import requests

from utils import get_coordinates, decode_weather_code, get_web_page_content

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="MCP Server",
)

# Definizione degli strumenti MCP
@mcp.tool()
def wikipedia_search(query: str) -> str:
    """
    Ottiene un riassunto da Wikipedia per una data query.
    """
    result = wikipedia.summary(query)
    return result

@mcp.tool()
def get_weather_by_city(city_name: str) -> dict:
    """
    Ottiene il meteo attuale per una città usando le API Open-Meteo e decodifica il weathercode.
    """
    lat, lon, timezone = get_coordinates(city_name)
    if lat is None or lon is None:
        return {
            "error": f"City '{city_name}' not found."
        }

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": timezone
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current_weather")

        if not current:
            return {"error": "Weather data not available."}

        # Decodifica il codice meteo
        code = current.get("weathercode")
        condition = decode_weather_code(code)

        # Aggiungi la condizione decodificata ai dati
        current["condition"] = condition
        return current

    except requests.RequestException as e:
        return {"error": str(e)}

# Definizione dei prompt MCP
@mcp.prompt()
def wikipedia_unict() -> str:
    """Searches Wikipedia for information about the University of Catania"""
    return "Cerca su Wikipedia informazioni sull'Università di Catania"

@mcp.prompt()
def catania_weather() -> str:
    """Searches for the weather in Catania"""
    return "Dammi le previsioni meteo per Catania"

@mcp.prompt()
def project_readme() -> str:
    """Gives informations about the project by reading the README file"""
    return "Dammi il README di questa applicazione streamlit a partire dalle risorse MCP"

@mcp.resource("web://aitho")
def aitho_web() -> str:
    """Fetches the content of the Aitho website."""
    return get_web_page_content("https://aitho.it/chi-siamo/")

@mcp.resource("file://readme")
def readme() -> str:
    """Legge un file Markdown e restituisce il contenuto come testo semplice."""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")

    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        return md_text
    except Exception as e:
        return f"Errore durante la lettura del file Markdown: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
