import requests
import argparse
import logging
import json
import openai
import re
import colorlog
from urllib.parse import urlparse
from pyAutoBot import DBHandler, Website
from config import HEADERS, SITE_URL, BASE_PAYLOAD
from bs4 import BeautifulSoup
from pyAutoBot.agenzie import Gabetti
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
    @staticmethod
    def clean_name(name: str) -> str:
        # check if we have already Agenzia Immobiliare in the name, otherwise add it
        if 'Agenzia Immobiliare' not in name:
            name =  f"Agenzia Immobiliare {name}"
        # clean Tempocasa case, removing everything after it
        pattern = "(Agenzia Immobiliare Tempocasa).*"
        name = re.sub(pattern, r'\1', name)
        # clean RE/MAX case, removing everything after it
        pattern = "(Agenzia Immobiliare RE/MAX).*"
        name = re.sub(pattern, r'\1', name)
        # clean Tecnocasa case, removing everything after it
        pattern = "(Agenzia Immobiliare Tecnocasa).*"
        name = re.sub(pattern, r'\1', name)        
        # clean Affiliato Tecnocasa case, removing everything after it
        pattern = "(Agenzia Immobiliare Affiliato Tecnocasa).*"
        name = re.sub(pattern, r'\1', name)
        pattern = "(Agenzia Immobiliare Affiliato RE/MAX).*"
        name = re.sub(pattern, r'\1', name)
        pattern = "(Agenzia Immobiliare Affiliato Gabetti).*"
        return name
    
    @staticmethod
    def create_base_payload(data_dict, agid):
        logger.info(f"Creating base payload for url: {data_dict['url']}")

        data_dict = data_dict
        agenzia = None
        nomeente = ""
        # if we know how to handle it, let's handle it with the class
        if 'Gabetti' in data_dict['nomeente']:
            agenzia = Gabetti(data_dict['url'], logger=logger.getChild(Gabetti.__name__))
            nomeente = agenzia.get_name(data_dict['nomeente'])
        if agenzia is None:
            # Extrapolate data with AI
            data_extractor = DataExtraction(logger.getChild(DataExtraction.__name__))
            ex_data = data_extractor.try_to_extrapolate_data(data_dict['url'])
            logger.info(f"Extrapolated data: {ex_data}")
            chi_siamo = ex_data['chisiamo']
            email = ex_data['email']
            nomeente = PayloadHandler.clean_name(data_dict['nomeente'])
        else:
            chi_siamo = agenzia.get_description()
            email = agenzia.get_email()
        
        base_payload = BASE_PAYLOAD
        base_payload['url'] = data_dict['url']
        
        base_payload['nomeente'] = nomeente
        base_payload['telefonostandard'] = f"{data_dict['telefonostandard']}"
        base_payload['indirizzo'] = data_dict['indirizzo']
        base_payload['cap'] = data_dict['cap']
        base_payload['localita'] = data_dict['localita0']
        base_payload['localitacartella'] = data_dict['localitacartella0'].lower()
        base_payload['provincia'] = data_dict['localitaprovincia0']
        base_payload['agid'] = agid
        base_payload['chisiamo'] = chi_siamo.encode('latin-1', errors='ignore').decode('unicode_escape')
        base_payload['email'] = email
        return base_payload

class Scrapper:
    def __init__(self, agid: int, execute: bool, confirm: bool):
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self.data_extractor = DataExtraction(logger.getChild(DataExtraction.__name__))
        self._data_dict =  RequestHandler._load_agency_from_site(f"{SITE_URL}/agenzia-mod.php?agid={self.agid}")
        self.payload_handler = PayloadHandler()
        self.url = self._data_dict['url']
        self.confirm = confirm
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self):
        base_uri = Utility.get_base_uri(self.url)
        self.db_handler.init_db()
        session = self.db_handler.get_session()
        base_uri = base_uri.rstrip('/')
        website = session.query(Website).filter(Website.url.like(f"{base_uri}%")).first()
        
        # if base_uri is present in websites nomeent column, then load the payload from the database
        if website is not None:
            self.logger.info(f"Loading payload from database for base_uri: {base_uri}")
            # we take information from the database, but 
            # the field telefonostandard, indirizzo, cap localita, localitacartella, provincia
            # will be taken by the data_dict
            data_payload = {column.name: getattr(website, column.name) for column in Website.__table__.columns if column.name != "id"}
            # overwrite the filed from data_dict
            data_payload['telefonostandard'] = self._data_dict['telefonostandard']
            data_payload['indirizzo'] = self._data_dict['indirizzo']
            data_payload['cap'] = self._data_dict['cap']
            data_payload['localita'] = self._data_dict['localita0']
            data_payload['localitacartella'] = self._data_dict['localitacartella0'].lower()
            data_payload['provincia'] = self._data_dict['localitaprovincia0']
            data_payload['url'] = self._data_dict['url']
            # try to extrapolate the description
            ex_data = self.data_extractor.try_to_extrapolate_data(data_payload['url'])
            self.logger.info(f"Extrapolated data: {ex_data}")
            chi_siamo = ex_data['chisiamo']
            email = ex_data['email']
            data_payload['chisiamo'] = chi_siamo.encode('latin-1', errors='ignore').decode('unicode_escape')
            data_payload['email'] = email
            if 'Mi dispiace' in data_payload['chisiamo']:
                # we failed retrieving via AI the description let's use the one from the database,
                # make it general via open ai
                self.logger.info(f"Failed retrieving description via AI, using the one from the database...")
                data_payload['chisiamo'] = self.data_extractor.generalize_description(data_payload['chisiamo'])
                if data_payload['chisiamo'] == 'Error retrieving data.':
                    self.logger.error(f"Error retrieving data from openai, manual input...")
                    data_payload['chisiamo'] = input("Insert description: ")
        else:
            self.logger.warning(f"We don't have this base_uri in our database: {base_uri}, we try to load the informations...")
            self.logger.warning(f"")
            data_payload = self.payload_handler.create_base_payload(self._data_dict, self.agid)
            # localita1, localitaprovincia1 and localitacartella1 will be the same as localita and localitacartella
            data_payload['localita1'] = data_payload['localita']
            data_payload['localitaprovincia1'] = data_payload['provincia']
            data_payload['localitacartella1'] = data_payload['localitacartella']
            data_payload['noemail'] = 'Y' if data_payload['email'] == '' else 'N'
            # Sanitize description
            if 'Mi dispiace' in data_payload['chisiamo']:
                # we failed retrieving via AI the description, let's do it manually in this case
                self.logger.info(f"Failed retrieving description via AI, manual input...")
                data_payload['chisiamo'] = input("Insert description: ")
            
        if self.execute:
            self.logger.info(f"Payload: {json.dumps(data_payload, indent=4)}")
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
            
            response = RequestHandler.execute_request(self.agid, data_payload, HEADERS)
            if response.status_code == 200:
                self.logger.info(f"Request executed successfully")
                # save payload to database
                self.logger.info(f"Saving payload to database")
                website = Website(**data_payload)
                session.add(website)
                session.commit()
                self.logger.info(f"Payload saved to database")
        else:
            self.logger.info(f"Execute flag is set to False, skipping request execution")
            self.logger.info(f"Payload: {json.dumps(data_payload, indent=4)}")
            
# The main execution code remains the same
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='167')
    parser.add_argument('--execute', help='execute request, default is False', default=False, action='store_true')
    parser.add_argument('--confirm', help='confirm request execution', default=False, action='store_true')
    parser.add_argument('--debug', help='debug mode', default=False, action='store_true')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)

    scraper = Scrapper(args.agid, args.execute, args.confirm)
    scraper.run()
