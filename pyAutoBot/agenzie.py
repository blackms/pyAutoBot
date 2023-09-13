import requests
import logging
import re
import json
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from .data_extraction import DataExtraction
from config import BASE_PAYLOAD
from collections import Counter


class Agenzia:
    def __init__(self, url: str, logger: logging.Logger, use_AI: bool = False):
        self.url = url
        self.headers =  {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        self.logger = logger
        self.payload = BASE_PAYLOAD
        self.use_AI = use_AI
        
    def _load_html(self):
        self.logger.critical(f"Loading HTML for {self.url}...")
        response = requests.get(self.url, headers=self.headers)
        if response.status_code == 200:
            self.soup = BeautifulSoup(response.text, 'html.parser')
    
    @abstractmethod
    def get_email(self):
        raise NotImplementedError
    
    @abstractmethod
    def get_description(self):
        raise NotImplementedError
    
    @abstractmethod
    def get_lista_immobili(self):
        pass
    
    def get_payload(self):
        return self.payload
    
    def is_agenzia_vacanze(self):
        name_keywords = [
            'casa vacanze', 'appartamenti per vacanze', 
            'affitti brevi', 'affitti turistici', 'affitti per vacanze', 
            'appartamenti', 'vacanze', 'vacanza'
        ]
        
        chi_siamo_keywords = [
            'breakfast', 'vacanza', 'vacanze', 'appartamenti', 
            'appartamento', 'tour', 'touring'
        ]
        
        for name_keyword in name_keywords:
            if name_keyword in self.payload['nomeente'].lower():
                return True
        for chi_siamo_keyword in chi_siamo_keywords:
            if chi_siamo_keyword in self.payload['chisiamo'].lower():
                return True
    
    
class Generica(Agenzia):
    def __init__(self, url, logger: logging.Logger, use_AI: bool = False):
        super().__init__(url, logger, use_AI)
        self.soup = None
        self.logger.getChild(__name__).info(f"Generica object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)

    
class Gabetti(Agenzia):
    def __init__(self, url, logger: logging.Logger, use_AI: bool = False):
        super().__init__(url, logger)
        self.soup = None
        self.logger.getChild(__name__).info(f"Gabetti object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
        self.use_AI = use_AI
        
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
        return self.payload['chisiamo']
    
    def get_name(self):
        self.payload['nomeente'] = 'Agenzia Immobiliare Gabetti'
        return self.payload['nomeente']
    
    
class Remax(Agenzia):
    def __init__(self, url, logger: logging.Logger, use_AI: bool = True):
        super().__init__(url, logger, use_AI)
        self.soup = None
        self.logger.getChild(__name__).info(f"Remax object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
        self.__init_soup()
        
    def __init_soup(self):
        self.soup = self.data_extraction.get_soup(self.url)
        
    def get_email(self):
        self.payload['email'] = 'info@remax.it'
        return 'info@remax.it'
    
    def get_description(self):
        default_text = "RE/MAX è un'agenzia immobiliare italiana che mira all'eccellenza, basandosi su fiducia, qualità e collaborazione, con un forte impegno nella formazione degli agenti e nel sostegno sociale, in particolare verso Telefono Azzurro e Dynamo Camp."
        description = default_text
        
        if self.use_AI:
            try:
                self.logger.info("Trying to retrieve description via AI...")
                description = self.data_extraction.try_parse_description(self.soup.get_text(separator=' ', strip=True))
                if description is None or 'Mi dispiace' in description:
                    raise ValueError("Invalid description retrieved")
                self.logger.warning(f"Description: {description}")
            except Exception as e:
                self.logger.error(f"Error while trying to parse description: {e}")
                description = default_text
        
        self.payload['chisiamo'] = description
        return description

        
    def get_name(self):
        self.payload['nomeente'] = 'Agenzia Immobiliare RE/MAX'
        return self.payload['nomeente']
        
    def __get_lista_immobili_link(self):
        # get the base uri
        parsed_uri = urlparse(self.url)
        base_uri = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        base_uri = base_uri.rstrip('/')
        link = self.soup.find('a', class_='agency-page__more')['href']
        self.logger.debug(f"Base uri: {base_uri}")
        self.logger.debug(f"Links: {link}")
        if 'order=sell_price-desc' in link:
            self.logger.info(f"Found immobili link: {base_uri+link}")
            return base_uri+link
        
    def get_lista_immobili(self):
        self.logger.info("Trying to retrieve the list of properties...")
        immobili_link = self.__get_lista_immobili_link()
        if not immobili_link:
            self.logger.error("No immobili link found.")
            return None
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(immobili_link, headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Error while trying to retrieve immobili list: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        immobili = soup.find_all('div', class_='search-item__location')
        if not immobili:
            self.logger.info("No immobili found.")
            return None
        
        properties = []
        self.logger.info(f"Found {len(immobili)} immobili.")
        for immobile in immobili:
            location_text = immobile.text.strip()
            try:
                city, province = location_text.split(', ')
            except ValueError:
                # this means that the data is not completed, province is missing, skip it.
                continue
            properties.append({'City': city, 'Province': province})
        
        # Count and sort by occurrences
        location_counts = Counter(tuple(location.items()) for location in properties)
        sorted_locations_with_count = [{'location': dict(location), 'count': count} for location, count in location_counts.most_common()]
        self.logger.warning(f"Immobili: {json.dumps(sorted_locations_with_count, indent=4)}")
        return properties
        

class Toscano(Agenzia):
    def __init__(self, url, logger: logging.Logger, use_AI: bool = False):
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
        self.payload['nomeente'] = 'Agenzia Immobiliare Toscano'
        return self.payload['nomeente']


class Tecnorete(Agenzia):
    def __init__(self, url, logger: logging.Logger, use_AI: bool = False):
        super().__init__(url, logger)
        self.soup = None
        self.logger.getChild(__name__).info(f"Tecnorete object created for {self.url}")
        self._load_html()
        self.data_extraction = DataExtraction(self.logger)
    
    def get_email(self):
        # Find the anchor tag with the 'mailto' in its href attribute
        email_tag = self.soup.find('a', href=lambda x: x and 'mailto:' in x)
        # Extract the email
        email = email_tag.text if email_tag else None
        self.payload['email'] = email
        return email
    
    def get_description(self):
        self.payload['chisiamo'] = "Il marchio Tecnocasa è nato nel 1979 da Oreste Pasquali, focalizzandosi sull'intermediazione immobiliare nell'hinterland milanese. Nel corso degli anni, Tecnocasa si è espansa a livello internazionale, ha acquisito e lanciato vari marchi e servizi, ed è diventata una figura chiave nel settore immobiliare e creditizio, culminando con fusioni e acquisizioni nel 2022."
        return self.payload['chisiamo']
    
    def get_name(self):
        self.payload['nomeente'] = 'Agenzia Immobiliare Tecnorete'
        return self.payload['nomeente']
        