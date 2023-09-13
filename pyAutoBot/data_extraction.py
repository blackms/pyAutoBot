import requests
import logging
import re
import openai
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from secret import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY



class DataExtraction:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"

    def __init__(self, logger: logging.Logger):
        self.logger = logger.getChild(__name__)
        openai.api_key = OPENAI_API_KEY

    def _send_openai_request(self, messages):
        try:
            return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
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

    def get_soup(self, url: str) -> BeautifulSoup:
        response = requests.get(url, headers=self.HEADERS)
        return BeautifulSoup(response.text, 'html.parser')
    
    