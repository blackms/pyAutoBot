import requests
import logging
import re
import openai
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from secret import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY



class DataExtractor:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"

    def __init__(self, logger: logging.Logger):
        self.logger = logger.getChild(__name__)
        openai.api_key = OPENAI_API_KEY
        with open('comuni.json', 'r') as data:
            self.comuni = json.load(data)
        
    def _find_city(self, text: str) -> dict:
        for entry in self.comuni:
            # Verifica se il nome della città è seguito da uno spazio o se è alla fine del testo
            pattern = re.compile(r'\b' + re.escape(entry['nome']) + r'(\s|$)')
            if pattern.search(text):
                return {
                    'nome': entry['nome'],
                    'provincia': entry['provincia']['nome'],
                    'sigla': entry['sigla']
                }
        return None

    def _send_openai_request(self, messages):
        try:
            return openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages=messages)
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return None

    def try_to_extrapolate_data(self, url):
        response = requests.get(url, headers=self.HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        emails = re.findall(self.EMAIL_PATTERN, soup.get_text())
        email = emails[0] if emails else f"info@{urlparse(url).netloc.replace('www.', '')}"

        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": f"Estrapola dal seguente testo una descrizione dell'agenzia: {text_content}"}
        ]
        response = self._send_openai_request(messages)
        summary = response['choices'][0]['message']['content'].strip() if response else "Error retrieving data."

        return {'chisiamo': summary, 'email': email}

    def generalize_description(self, desc: str) -> str:
        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": f"Generalizza il seguente testo togliendo riferimenti a nomi: {desc}"}
        ]
        response = self._send_openai_request(messages)
        return response['choices'][0]['message']['content'].strip() if response else "Error retrieving data."

    def try_parse_description(self, desc: str) -> str:
        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": f"Prova ad estrapolare una descrizione dell'agenzia immobiliare dal seguente testo: {desc}"}
        ]
        response = self._send_openai_request(messages)
        return response['choices'][0]['message']['content'].strip() if response else "Error retrieving data."
    
    def try_parse_phone_number(self, agenzia) -> str:
        text = agenzia.soup.get_text(separator=' ', strip=True)
        messages = [
            {"erols": "system", "content": "Sei un API di un portale di annunci immobiliari. Riceverai del testo e ritornerai la risposta senza aggiungere testo."},
            {"roles:": "user", "content": f"Prova ad estrapolare un numero di telefono dal seguente testo: {text}"}
        ]
        response = self._send_openai_request(messages)
        return response['choices'][0]['message']['content'].strip() if response else "Error retrieving data."
    
    def try_extract_locations_from_text(self, agenzia) -> list:
        text = agenzia.soup.get_text(separator=' ', strip=True)
        messages = [
            {"role": "system", "content": "Sei un API di un portale di annunci immobiliari. Riceverai del testo e ritornerai la risposta senza aggiungere testo."},
            {"role": "user", "content": "Estrai e restituisci solo la lista delle città in formato JSON dal seguente testo:" + text}
        ]
        response = self._send_openai_request(messages)

        found_locations = response['choices'][0]['message']['content'].strip()
        self.logger.info(f"Found location: {found_locations}")

        if 'Mi dispiace' in found_locations:
            self.logger.warning(f"Failed retrieving locations via AI. Using parser method")
            return []

        try:
            loaded_data = json.loads(found_locations)
        except json.decoder.JSONDecodeError:
            self.logger.error(f"Cannot parse locations from AI. Using only the default location")
            self.logger.debug(f"Response from AI: {found_locations}")
            return []
        
        if isinstance(loaded_data, dict):
            found_locations = list(loaded_data.values())
        else:
            found_locations = loaded_data

        self.logger.info(f"Found location: {found_locations}")

        flat_locations = [item for sublist in found_locations for item in sublist]
        locations = [self._find_city(location) for location in flat_locations if location]

        # Filtra eventuali valori None dalla lista prima di restituirla
        return [location for location in locations if location]

    def get_soup(self, url: str) -> BeautifulSoup:
        response = requests.get(url, headers=self.HEADERS)
        return BeautifulSoup(response.text, 'html.parser')
    
    