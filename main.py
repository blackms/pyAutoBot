import requests
import argparse
import logging
import json
import openai
import re
import colorlog
from urllib.parse import urlparse
from pyAutoBot import DBHandler, Website
from config import HEADERS, SITE_URL
from bs4 import BeautifulSoup
from pyAutoBot.agenzie import Gabetti, Remax, Toscano, Generica, Tecnorete
from pyAutoBot.data_extraction import DataExtraction

# Setup logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

openai.api_key = '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'

class Utility:
    @staticmethod
    def get_base_uri(url):
        parsed_uri = urlparse(url)
        base_uri = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return base_uri.rstrip('/')
    
    # Other utility methods can be added here

class RequestHandler:
    @staticmethod
    def execute_request(agid, data_payload, headers):
        complete_url = f"{SITE_URL}/agenzia-mod-do.php?agid={agid}"
        logger.info(f"Executing request to {complete_url} with payload: {json.dumps(data_payload, indent=4)}")
        response = requests.post(complete_url, data=data_payload, headers=headers)
        logger.info(f"Response received from {complete_url}: {response.status_code}")
        return response
    
    @staticmethod
    def _load_agency_from_site(url):
        logger.info(f"Loading agency from site: {url}")
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7',
            'Connection': 'keep-alive',
            'Cookie': 'username=zia; pmd=76795032372222d2c36402b760908586; primoref=https%3A%2F%2Fwww.ultimissimominuto.com%2Feditors%2Fdashboard.php; PHPSESSID=cc8apjv3lmns4pifmrciuis9ml',
            'Referer': 'https://www.ultimissimominuto.com/editors/agenzia-lista.php',
            'Sec-Fetch-Dest': 'frame',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'sec-ch-ua': '\"Chromium\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Google Chrome\";v=\"116\"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '\"Windows\"'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extract JSON data from the script tag
        inputs = soup.find_all('input')

        data_dict = {}

        for inp in inputs:
            input_id = inp.get('id')
            input_value = inp.get('value', '')
            if input_id:
                data_dict[input_id] = input_value
        logger.debug(f"Extracted data: {json.dumps(data_dict, indent=4)}")
        return data_dict
        pass

class PayloadHandler:
    def __init__(self, logger):
        self.logger = logger.getChild(__name__)
        
    def clean_name(self, name: str) -> str:
        self.logger.info(f"Cleaning name: {name}")
        if 'Agenzia Immobiliare' not in name:
            name = f"Agenzia Immobiliare {name}"
        patterns = [
            "(Agenzia Immobiliare Tempocasa).*",
            "(Agenzia Immobiliare RE/MAX).*",
            "(Agenzia Immobiliare Tecnocasa).*",
            "(Agenzia Immobiliare Affiliato Tecnocasa).*",
            "(Agenzia Immobiliare Affiliato RE/MAX).*",
            "(Agenzia Immobiliare Progetto Casa Napoli).*",
            "(Agenzia Immobiliare ScegliCasa Roma).*"
        ]
        for pattern in patterns:
            name = re.sub(pattern, r'\1', name)
        special_cases = {
            "Toscano.* Agenzia Immobiliare": 'Agenzia Immobiliare Toscano',
            "Agenzia Immobiliare 7Case.*": 'Agenzia Immobiliare 7Case',
            "Agenzia Leonardo Immobiliare.*": "Agenzia Leonardo Immobiliare",
        }
        for pattern, replacement in special_cases.items():
            if re.search(pattern, name):
                name = replacement
                break
        return name
    
    
    def create_base_payload(self, data_dict, agid):
        self.logger.info(f"Creating base payload for url: {data_dict['url']}")
        self.logger.info(f"We don't know how to handle this agency, let's try to extrapolate data...")
        
        data_extractor = DataExtraction(self.logger)
        ex_data = data_extractor.try_to_extrapolate_data(data_dict['url'])
        self.logger.debug(f"Extrapolated data: {ex_data}")
        chi_siamo = ex_data['chisiamo']
        email = ex_data['email']
        payload_handler = PayloadHandler(self.logger)
        nomeente = payload_handler.clean_name(name=data_dict['nomeente'])

        base_payload = {
            'url': data_dict['url'],
            'nomeente': nomeente,
            'telefonostandard': f"{data_dict['telefonostandard']}",
            'indirizzo': data_dict['indirizzo'],
            'cap': data_dict['cap'],
            'localita': data_dict['localita0'],
            'localitacartella': data_dict['localitacartella0'].lower(),
            'provincia': data_dict['localitaprovincia0'],
            'agid': agid,
            'chisiamo': chi_siamo.encode('latin-1', errors='ignore').decode('unicode_escape'),
            'email': email
        }
        return base_payload

class Scrapper:
    def __init__(self, agid: int, execute: bool, confirm: bool, use_ai: bool = False):
        self.logger = logger.getChild(self.__class__.__name__)
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self.data_extractor = DataExtraction(self.logger)
        self._data_dict =  RequestHandler._load_agency_from_site(f"{SITE_URL}/agenzia-mod.php?agid={self.agid}")
        self.payload_handler = PayloadHandler(self.logger)
        self.url = self._data_dict['url']
        self.confirm = confirm
        self.use_ai = use_ai
        
    def initialize(self):
        self.base_uri = Utility.get_base_uri(self.url)
        self.db_handler.init_db()
        self.session = self.db_handler.get_session()
        self.base_uri = self.base_uri.rstrip('/')
        
    def get_agenzia_instance(self, nomeente, url):
        agenzia = None
        agency_map = {
            'Gabetti': Gabetti,
            'RE/MAX': Remax,
            'Toscano': Toscano,
            'Tecnorete': Tecnorete
        }

        for agency_name, agency_class in agency_map.items():
            if agency_name in nomeente:
                agenzia = agency_class(url, logger=self.logger, use_AI=self.use_ai)
                nomeente = agenzia.get_name()
                break

        return agenzia
    
    def handle_unknown_agency(self, url: str):
        # We don't have this agency in our classes, use generic one and try extrapolate data
        self.logger.info(f"We don't have this agency in our classes, use generic one and try extrapolate data...")
        agenzia = Generica(url, logger=self.logger, use_AI=self.use_ai)
        
        agenzia.payload['nomeente'] = self.payload_handler.clean_name(self._data_dict['nomeente'])
        self.logger.info(f"Cleaned name: {agenzia.payload['nomeente']}")
        # input name of the agency
        agenzia.payload['nomeente'] = input("Insert name of the agency: ")
        agenzia.payload['telefonostandard'] = self._data_dict['telefonostandard']
        agenzia.payload['indirizzo'] = self._data_dict['indirizzo']
        agenzia.payload['cap'] = self._data_dict['cap']
        agenzia.payload['localita'] = self._data_dict['localita0']
        agenzia.payload['localitacartella'] = self._data_dict['localitacartella0'].lower()
        agenzia.payload['provincia'] = self._data_dict['localitaprovincia0']
        agenzia.payload['url'] = self._data_dict['url']
        agenzia.payload['agid'] = self.agid
        agenzia.payload['localita1'] = agenzia.payload['localita']
        agenzia.payload['localitacartella1'] = agenzia.payload['localitacartella']
        agenzia.payload['localitaprovincia1'] = agenzia.payload['provincia']

        # try to extrapolate the description
        try:
            ex_data = self.data_extractor.try_to_extrapolate_data(agenzia.payload['url'])
            self.logger.warning(f"Extrapolated data: {ex_data}")
            chi_siamo = ex_data['chisiamo']
        except openai.error.RateLimitError:
            self.logger.error(f"Rate limit reached, manual input...")
            agenzia.payload['chisiamo'] = ''
            pass 

        email = re.sub(r'^\d+|(@gmail\.com).*$', r'\1', ex_data['email'])
        
        agenzia.payload['chisiamo'] = chi_siamo.encode('latin-1', errors='ignore').decode('unicode_escape')
        agenzia.payload['email'] = email
        agenzia.payload['noemail'] = 'Y' if agenzia.payload['email'] == '' else 'N'
        if 'Mi dispiace' in agenzia.payload['chisiamo'] or agenzia.payload['chisiamo'] == '':
            # failed to retrieve data from AI
            self.logger.warning(f"Failed retrieving description via AI, manual input...")    
            self.logger.error(f"Error retrieving data from openai, manual input...")
            agenzia.payload['chisiamo'] = input("Insert description: ")
        
        return agenzia
    
    
    def handle_known_agency(self, agenzia):
        self.logger.info(f"We have the agency in our classes, use the class to extrapolate data...")
        self.logger.warning(f"We already know how to handle this agency: {agenzia.payload['nomeente']}, using the description from the class...")
        agenzia.payload['telefonostandard'] = self._data_dict['telefonostandard']
        agenzia.payload['indirizzo'] = self._data_dict['indirizzo']
        agenzia.payload['cap'] = self._data_dict['cap']
        agenzia.payload['localita'] = self._data_dict['localita0']
        agenzia.payload['localitacartella'] = self._data_dict['localitacartella0'].lower()
        agenzia.payload['provincia'] = self._data_dict['localitaprovincia0']
        agenzia.payload['url'] = self._data_dict['url']
        agenzia.payload['agid'] = self.agid
        agenzia.payload['chisiamo'] = agenzia.get_description()
        agenzia.payload['email'] = agenzia.get_email()
        agenzia.payload['nomeente'] = agenzia.get_name()
        agenzia.payload['localita1'] = agenzia.payload['localita']
        agenzia.payload['localitacartella1'] = agenzia.payload['localitacartella']
        agenzia.payload['localitaprovincia1'] = agenzia.payload['provincia']
        # try to identify where do they operate
        immobili = agenzia.get_lista_immobili()
        
        return agenzia
    
    
    def ask_user_confirmation(self, agenzia):
        if self.execute:
            self.logger.info(f"Payload: {json.dumps(agenzia.payload, indent=4)}")
            if not self.confirm:
                while True:
                    user_input = input("Do you want to continue? (Y/N): ")
                    if user_input in ['Y', 'N', 'y', 'n']:
                        if user_input == 'N' or user_input == 'n':
                            logger.info(f"Exiting...")
                            exit(0)
                        break
                    else:
                        print("Invalid input. Please enter 'Y' or 'N'.")
        else:
            self.logger.info(f"Execute flag is set to False, skipping request execution")
            self.logger.info(f"Payload: {json.dumps(agenzia.payload, indent=4)}")
          
            
    def execute_request(self, agenzia):
        website = self.session.query(Website).filter(Website.url.like(f"{self.base_uri}%")).first()
        response = RequestHandler.execute_request(self.agid, agenzia.payload, HEADERS)
        if response.status_code == 200:
            self.logger.info(f"Request executed successfully")
            # save payload to database
            self.logger.info(f"Saving payload to database")
            website = Website(**agenzia.payload)
            self.session.add(website)
            self.session.commit()
            self.logger.info(f"Payload saved to database")
            
            
    def run(self):
        self.initialize()
        nomeente = self._data_dict['nomeente']
        url = self._data_dict['url']

        agenzia = self.get_agenzia_instance(nomeente, url)
        if agenzia is None:
            agenzia = self.handle_unknown_agency(url)
        else:
            agenzia = self.handle_known_agency(agenzia)
            
        self.ask_user_confirmation(agenzia)        
        self.execute_request(agenzia)
            



            
# The main execution code remains the same
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='88')
    parser.add_argument('--execute', help='execute request, default is False', default=False, action='store_true')
    parser.add_argument('--confirm', help='confirm request execution', default=False, action='store_true')
    parser.add_argument('--debug', help='debug mode', default=False, action='store_true')
    parser.add_argument('--use-ai', help='use AI to extrapolate data', default=False, action='store_true')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)

    scraper = Scrapper(args.agid, args.execute, args.confirm)
    scraper.run()
