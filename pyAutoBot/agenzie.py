import requests
import logging
import re
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from .data_extraction import DataExtraction


class Agenzia:
    def __init__(self, url: str, logger: logging.Logger):
        self.url = url
        self.headers =  {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        self.logger = logger
        
    def _load_html(self):
        response = requests.get(self.url, headers=self.headers)
        if response.status_code == 200:
            self.soup = BeautifulSoup(response.text, 'html.parser')
    
    @abstractmethod
    def get_email(self):
        raise NotImplementedError
    
    @abstractmethod
    def get_description(self):
        raise NotImplementedError
    
    
class Gabetti(Agenzia):
    def __init__(self, url, logger: logging.Logger):
        super().__init__(url, logger)
        self.soup = None
        self.logger.getChild(__name__).info(f"Gabetti object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
        
    def get_email(self):
        email_link = self.soup.find('a', class_='icon icon-email')

        if email_link:
            email = email_link.get_text().strip()
            self.logger.info(f"Email found: {email}")
            return email
        else:
            self.logger.info("Email not found.")
            return None
    
    def get_description(self):
        msg = "Il nostro Gruppo – oltre settant’anni di attività, società quotata in borsa dal 1990, iscritta al registro dei marchi storici italiani – è in Italia l’unico Full Service Provider per l’intero sistema immobiliare, un modello unico rispetto agli altri operatori. Offriamo consulenza integrata in tutti i settori del Real Estate per soddisfare esigenze e aspettative di privati, aziende e operatori istituzionali. "
        msg += "Il nostro sistema organizzativo si fonda sull’integrazione e il coordinamento delle competenze specifiche di ciascuna società del Gruppo nell’ambito delle seguenti aree: Consulenza, Valorizzazione, Gestione, Intermediazione, Mediazione Creditizia e Assicurativa, Riqualificazione. "
        msg += "Siamo l’unico player ad avere sedi corporate in tutti i maggiori capoluoghi con presidio regionale e siamo presenti capillarmente in tutta Italia con le nostre reti in franchising: oltre 1.200 agenzie immobiliari e 1.300 imprese nell’ambito della riqualificazione."
        return msg
    
    def get_name(self, name: str):
        return "Agenzia Immobiliare Gobetti"