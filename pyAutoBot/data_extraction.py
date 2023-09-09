import requests
import logging
import re
import openai
from urllib.parse import urlparse
from bs4 import BeautifulSoup


openai.api_key = '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'


class DataExtraction:
    def __init__(self, logger: logging.Logger):
        self.logger = logger.getChild(__name__)
        
    
    def try_to_extrapolate_data(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Use the OpenAI Completion API to process the "Who We Are" section
        text_content = soup.get_text(separator=' ', strip=True)
        self.logger.debug(f"Text content: {text_content}")
        # Define a regular expression pattern for typical email formats
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"
    
        # Search the entire webpage content for emails
        try:
            emails = re.findall(email_pattern, soup.get_text())[0]
        except IndexError:
            self.logger.error(f"Email not found, setting default to info...")
            # extrapolate the domain for the url
            domain = urlparse(url).netloc.replace("www.", "")
            emails = f"info@{domain}"
        self.logger.info(f"Emails: {emails}")
        # Set up the chat-based interaction
        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": 
                f"Estrapola dal seguente testo una descrizione dell'agenzia: {text_content}"}
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  
                messages=messages
            )
        except openai.error.InvalidRequestError:
            self.logger.error(f"Text is too long, insert manually...")
            summary = input("Insert summary: ")
            return {'chisiamo': summary, 'email': emails}

        # Extract the assistant's response from the reply
        summary = response['choices'][0]['message']['content'].strip()
        return {'chisiamo': summary, 'email': emails}
    
    def generalize_description(self, desc: str) -> str:
        messages = [
            {"role:": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": 
                f"Generalizza il seguente testo togliendo riferimenti a nomi: {desc}"}
        ]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  
                messages=messages
            )
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return "Error retrieving data."
        
        return response['choices'][0]['message']['content'].strip()
    
    def try_parse_description(self, desc: str) -> str:
        messages = [
            {"role:": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": 
                f"Prova ad estrapolare una descrizione dell'agenzia immobiliare dal seguente testo: {desc}"}
        ]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  
                messages=messages
            )
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return "Error retrieving data."
        
        return response['choices'][0]['message']['content'].strip()