import requests
import logging
import re
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from .data_extraction import DataExtraction
from config import BASE_PAYLOAD


class Agenzia:
    def __init__(self, url: str, logger: logging.Logger):
        self.url = url
        self.headers =  {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        self.logger = logger
        self.payload = BASE_PAYLOAD
        
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
            self.payload['email'] = email
            return email
        else:
            self.logger.info("Email not found.")
            return None
    
    def get_description(self):
        msg = "Il nostro Gruppo – oltre settant’anni di attività, società quotata in borsa dal 1990, iscritta al registro dei marchi storici italiani – è in Italia l’unico Full Service Provider per l’intero sistema immobiliare, un modello unico rispetto agli altri operatori. Offriamo consulenza integrata in tutti i settori del Real Estate per soddisfare esigenze e aspettative di privati, aziende e operatori istituzionali. "
        msg += "Il nostro sistema organizzativo si fonda sull’integrazione e il coordinamento delle competenze specifiche di ciascuna società del Gruppo nell’ambito delle seguenti aree: Consulenza, Valorizzazione, Gestione, Intermediazione, Mediazione Creditizia e Assicurativa, Riqualificazione. "
        msg += "Siamo l’unico player ad avere sedi corporate in tutti i maggiori capoluoghi con presidio regionale e siamo presenti capillarmente in tutta Italia con le nostre reti in franchising: oltre 1.200 agenzie immobiliari e 1.300 imprese nell’ambito della riqualificazione."
        self.payload['chisiamo'] = msg
        return msg
    
    def get_name(self):
        self.payload['chisiamo'] = 'Agenzia Immobiliare Gobetti'
        return self.payload['chisiamo']
    
    
class Remax(Agenzia):
    def __init__(self, url, logger: logging.Logger):
        super().__init__(url, logger)
        self.soup = None
        self.logger.getChild(__name__).info(f"Remax object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
        
    def get_email(self):
        self.payload['email'] = 'info@remax.it'
        return 'info@remax.it'
    
    def get_description(self):
        # try to retrieve description via AI
        try:
            desc = self.data_extraction.try_parse_description(self.soap.get_text(separator=' ', strip=True))
            self.payload['chisiamo'] = desc
        except Exception as e:
            self.logger.error(f"Error while trying to parse description: {e}")
            pass
        if desc is None or 'Mi dispiace' in desc:
            # use the group standard one
            text = "RE/MAX è un\'agenzia immobiliare italiana che mira all\'eccellenza, basandosi su fiducia, qualità e collaborazione, con un forte impegno nella formazione degli agenti e nel sostegno sociale, in particolare verso Telefono Azzurro e Dynamo Camp."
            self.payload['chisiamo'] = text
            return text
        

class Toscano(Agenzia):
    def __init__(self, url, logger: logging.Logger):
        super().__init__(url, logger)
        self.soup = None
        self.logger.getChild(__name__).info(f"Toscano object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
        
    def get_email(self):
        self.payload['email'] = 'info@toscano.it'
        return self.payload['email']
    
    def get_description(self):
        self.payload['chisiamo'] = "Dal 1982 ad oggi sono passati molti anni preziosi per il nostro gruppo. Da oltre 40 anni accompagniamo le famiglie italiane a vendere e comprare il bene per loro più importante: la casa. Consapevoli del valore sia dal punto di vista economico che affettivo, da sempre abbiamo l’obiettivo di offrire ai nostri clienti un servizio di alta qualità. Per farli sentire come a casa, curiamo l’immagine delle nostre agenzie, affinchè possano infondere accoglienza e serenità. Facciamo grande attenzione alla formazione dei nostri agenti e delle segretarie, che si relazionano con le famiglie. I nostri agenti sono dotati di mezzi tecnologici, di strumenti efficaci e innovativi per migliorare il rapporto con il cliente e la loro attività lavorativa. In tutti questi anni abbiamo acquisito un patrimonio di esperienza, che è il nostro strumento più prezioso, per cui, siamo in grado di soddisfare qualunque esigenza immobiliare in tutta Italia. Un risultato di cui siamo orgogliosi, e che ogni giorno ci spinge ad impegnarci sempre di più con passione e professionalità."
        return self.payload['chisiamo']
    
    def get_name(self):
        self.payload['nomeente'] = 'Toscano Immobiliare'
        return self.payload['nomeente']