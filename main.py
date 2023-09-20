import argparse
import json
import logging
import re
import concurrent.futures
from urllib.parse import urlparse

import colorlog
import openai
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from validate_email import validate_email

from config import HEADERS, SITE_URL
from pyAutoBot import DBHandler, Website
from pyAutoBot.Agenzie import Gabetti, Generica, Remax, Tecnorete, Toscano
from pyAutoBot.DataExtractor import DataExtractor
from pyAutoBot.PayloadHandler import PayloadHandler
from pyAutoBot.RequestHandler import RequestHandler
from pyAutoBot.Utility import Utility
from secret import OPENAI_API_KEY

# Setup logging
# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler
handler = colorlog.StreamHandler()

# Set a format for the handler
formatter = colorlog.ColoredFormatter(
    "%(log_color)s[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - "
    "%(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)

handler.setFormatter(formatter)
logger.addHandler(handler)

openai.api_key = OPENAI_API_KEY


class AgencyValidator:
    @staticmethod
    def is_valid_email(email):
        # Basic validation
        is_valid = validate_email(email)
        
        # Check if the domain of the email exists
        domain_exists = validate_email(email, check_mx=True)
        
        # Check if the email is accepted by the domain
        email_accepted = validate_email(email, verify=True)
        logger.info(f"Email: {email}, is_valid: {is_valid}, domain_exists: {domain_exists}, email_accepted: {email_accepted}")
        
        return is_valid

    @staticmethod
    def validate_agency_data(data):
        # Controlla che url, nomeente, telefonostandard non siano vuoti
        if not data.get('url') or not data.get('nomeente') or not data.get('telefonostandard'):
            return False, "URL, nomeente, or telefonostandard is empty."
        
        if 'Mi dispiace' in data.get('nomeente'):
            return False, "Nomeente contains 'Mi dispiace'."

        # Valida l'email tramite regex
        if not AgencyValidator.is_valid_email(data.get('email')):
            return False, "Email is not valid."

        # Controlla che noemail sia impostato su 'N'
        if data.get('noemail') != 'N':
            return False, "noemail is not set to 'N'."

        # Controlla che indirizzo, cap, localita, localitacartella non siano vuoti
        if not data.get('indirizzo') or not data.get('cap') or not data.get('localita') or not data.get('localitacartella'):
            return False, "indirizzo, cap, localita, or localitacartella is empty."

        # Controlla che provincia non sia vuoto
        if not data.get('provincia'):
            return False, "provincia is empty."

        # Controlla che localita1, localitaprovincia1, localitacartella1 non siano vuoti
        if not data.get('localita1') or not data.get('localitaprovincia1') or not data.get('localitacartella1'):
            return False, "localita1, localitaprovincia1, or localitacartella1 is empty."

        # Controlla che chisiamo non sia vuoto e contenga testo
        if not data.get('chisiamo') or not data['chisiamo'].strip():
            return False, "chisiamo is empty or does not contain text."
        
        if 'Error retrieving data.' in data.get('chisiamo'):
            return False, "chisiamo contains 'Error retrieving data.'."

        return True, "All checks passed."


class Scrapper:
    def __init__(self, agid: int, execute: bool, confirm: bool, use_ai: bool = False):
        self.logger = logger.getChild(self.__class__.__name__)
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self.reuest_handler = RequestHandler(self.logger)
        self._data_dict = self.reuest_handler.load_agency_from_site(
            f"{SITE_URL}/agenzia-mod.php?agid={self.agid}")
        self.payload_handler = PayloadHandler(self.logger)
        self.url = self._data_dict['url']
        self.confirm = confirm
        self.use_ai = use_ai
        self.geolocator = Nominatim(user_agent="pyAutoBotAgenzie")
        with open('comuni.json', 'r') as data:
            self.comuni = json.load(data)
        self.data_extractor = DataExtractor(self.logger)


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
                agenzia = agency_class(
                    url, logger=self.logger, use_AI=self.use_ai)
                nomeente = agenzia.get_name()
                break

        return agenzia

    def get_agency_name_confirmation(self, agenzia):
        if self.confirm:
            if not agenzia.payload['nomeente']:
                logger.error("Cannot retrieve agency name from AI.")
                self.reuest_handler.put_agency_under_review(agenzia)
                exit(1)
        else:
            logger.warning(
                f"Va bene il nome dell'agenzia per come e' ora?: {agenzia.payload['nomeente']}")
            while True:
                choice = input("Y/N: ").lower()
                if choice == 'n':
                    agenzia.payload['nomeente'] = input(
                        "Insert name of the agency: ")
                    break
                elif choice == 'y':
                    break
                else:
                    logger.warning("Invalid choice. Please enter 'Y' or 'N'.")
                    
    def _set_common_payload(self, agenzia):
        agenzia.payload['telefonostandard'] = self._data_dict['telefonostandard']
        agenzia.payload['indirizzo'] = self._data_dict['indirizzo']
        agenzia.payload['cap'] = self._data_dict['cap']
        agenzia.payload['localita'] = self._data_dict['localita0']
        agenzia.payload['localitacartella'] = self._data_dict['localitacartella0'].lower()
        agenzia.payload['provincia'] = self._data_dict['localitaprovincia0']
        agenzia.payload['url'] = self._data_dict['url']
        agenzia.payload['agid'] = self.agid
        agenzia.payload['localita1'] = agenzia.payload.get('localita')
        agenzia.payload['localitacartella1'] = agenzia.payload.get('localitacartella')
        agenzia.payload['localitaprovincia1'] = agenzia.payload.get('provincia')
        

    def decode_text(self, text):
        encodings = ['utf-8', 'latin1', 'iso-8859-1']  # Puoi aggiungere altre codifiche se necessario
        for encoding in encodings:
            try:
                return text.encode(encoding).decode('utf-8')
            except UnicodeDecodeError:
                continue
        return text  # Se nessuna codifica funziona, restituisci il testo originale

    def handle_unknown_agency(self, url: str):
        self.logger.info(
            "We don't have this agency in our classes, use generic one and try extrapolate data...")
        
        
        agenzia = Generica(url, logger=self.logger, use_AI=self.use_ai)
        
        self._set_common_payload(agenzia)
        try:
            agenzia.payload['nomeente'] = agenzia.extract_name_from_text(agenzia)
        except TypeError:
            self.logger.error(f"Cannot retrieve agency name from text.")
            self.logger.info("Moving agency in to_review.")
            self.reuest_handler.put_agency_under_review(agenzia)
            exit(0)
        self.logger.debug(f"Found name: {agenzia.payload['nomeente']}")
        self.get_agency_name_confirmation(agenzia)

        chi_siamo = ''
        # try to extrapolate the description
        try:
            ex_data = self.data_extractor.try_to_extrapolate_data(
                agenzia.payload.get('url'))
            self.logger.debug(f"Extrapolated data: {ex_data}")
            chi_siamo = ex_data.get('chisiamo', '')
        except openai.error.RateLimitError:
            self.logger.error("Rate limit reached, manual input...")

        # try to clean mail
        email = Utility.clean_email(ex_data.get('email', ''))
        is_valid = AgencyValidator.is_valid_email(email)
        chi_siamo = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), chi_siamo)

        
        agenzia.payload['email'] = "" if not is_valid else email
        agenzia.payload['noemail'] = 'Y' if agenzia.payload['email'] == '' else 'N'
        
        self.logger.info("Trying to extract description from text...")
        try:
            agenzia.payload['chisiamo'] = chi_siamo.encode('latin1').decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error: {e}")
            agenzia.payload['chisiamo'] = chi_siamo
            
        for i in range(2, 3):
            agenzia.payload.update({f'localita{i}': "", f'localitacartella{i}': "", f'localitaprovincia{i}': ""})

        try:
            locations = self.data_extractor.try_extract_locations_from_text(agenzia)
        except openai.error.InvalidRequestError:
            self.logger.error(f"Cannot retrieve properties locations from AI. Using parser method")
            locations = self.try_get_locations(agenzia.payload['url'])
            
        if locations:
            self.logger.info(f"Found locations in the text: {locations}")
            self.add_location_to_payload(agenzia, locations)

        # failed to retrieve data from AI
        if 'Mi dispiace' in agenzia.payload['chisiamo'] or agenzia.payload['chisiamo'] == '' or 'Error retrieving data.' in agenzia.payload['chisiamo']:
            self.logger.debug(agenzia.payload.get('chisiamo', ''))
            self.logger.error("Error retrieving data from openai")
            if not self.confirm:
                self.logger.warning("Failed retrieving description via AI, manual input...")
                agenzia.payload['chisiamo'] = input("Insert description: ")
            else:
                self.logger.warning("Failed retrieving description via AI, moving agency in to_review...")
                self.reuest_handler.put_agency_under_review(agenzia)
                exit(1)

        if agenzia.is_agenzia_vacanze():
            agenzia.payload['isaffittituristici'] = 'Y'
            
        if agenzia.payload['telefonostandard'] == '':
            try:
                agenzia.payload['telefonostandard'] = self.data_extractor.try_parse_phone_number(agenzia)
            except:
                self.logger.error("Error retrieving phone number from AI.")

        if self.confirm:
            is_valid, message = AgencyValidator.validate_agency_data(agenzia.payload)
            if not is_valid:
                self.logger.debug(json.dumps(agenzia.payload, indent=4))
                self.logger.critical(f"Invalid agency data: {message}")
                # put agency under review
                self.reuest_handler.put_agency_under_review(agenzia)

        return agenzia

    def get_distance_between_provinces(self, province1, province2):
        location1 = self.geolocator.geocode(f"{province1}, Italy")
        location2 = self.geolocator.geocode(f"{province2}, Italy")

        if location1 and location2:
            distance = geodesic((location1.latitude, location1.longitude), (location2.latitude, location2.longitude)).km
            return distance
        return float('inf')  # Return a large value if we can't get the location

    def add_location_to_payload(self, agenzia, locations):
        filters = ['napoli', 'canna']
        existing_locations = [agenzia.payload.get(f'localita{i}') for i in range(1, 4)]
        primary_province = agenzia.payload['localita1']

        for location in locations:
            distance = self.get_distance_between_provinces(primary_province, location['sigla'])
            self.logger.info(f"Distance between {primary_province} and {location['sigla']}: {distance} km")
            if location['nome'] not in filters and location['nome'] not in existing_locations and distance <= 50:
                index = None
                if not agenzia.payload['localita2']:
                    index = '2'
                elif not agenzia.payload['localita3']:
                    index = '3'

                if index:
                    agenzia.payload[f'localita{index}'] = location['nome']
                    agenzia.payload[f'localitacartella{index}'] = location['nome'].lower()
                    agenzia.payload[f'localitaprovincia{index}'] = location['sigla']

    def handle_known_agency(self, agenzia):
        self.logger.info(
            f"We already know how to handle this agency: {agenzia.payload['nomeente']}, using the description from the class...")
        
        self._set_common_payload(agenzia)
        agenzia.payload['agid'] = self.agid
        agenzia.payload['chisiamo'] = agenzia.get_description()
        agenzia.payload['email'] = agenzia.get_email()
        agenzia.payload['nomeente'] = agenzia.get_name()
        # try to identify where do they operate
        immobili = agenzia.get_lista_immobili()
        # try get locations from the text
        locations = self.try_get_locations(agenzia.payload['url'])
        if locations:
            logger.info(f"Found locations in the text: {locations}")
            for location in locations:
                if location['nome'].lower() != agenzia.payload['localita'].lower():
                    index = None
                    if not agenzia.payload['localita2']:
                        index = '2'
                    elif not agenzia.payload['localita3']:
                        index = '3'

                    if index:
                        agenzia.payload[f'localita{index}'] = location['nome']
                        agenzia.payload[f'localitacartella{index}'] = location['nome'].lower(
                        )
                        agenzia.payload[f'localitaprovincia{index}'] = location['provincia']
        return agenzia

    def try_get_locations(self, url: str) -> dict:
        self.logger.info(f"Trying to get locations from url: {url}")
        filtered_cities = []
        # get bs4 object
        soup = self.data_extractor.get_soup(url)
        # get the text
        text = soup.get_text()
        cnt = 0
        for entry in self.comuni:
            # Verifica se il nome della città è seguito da uno spazio o se è alla fine del testo
            pattern = re.compile(r'\b' + re.escape(entry['nome']) + r'(\s|$)')
            if pattern.search(text):
                filtered_cities.append({
                    'nome': entry['nome'],
                    'provincia': entry['provincia']['nome'],
                    'sigla': entry['sigla']
                })
                cnt += 1
                if cnt >= 2:
                    break
        return filtered_cities

    def ask_user_confirmation(self, agenzia):
        if self.execute:
            self.logger.info(
                f"Payload: {json.dumps(agenzia.payload, indent=4)}")
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
            self.logger.info(
                f"Execute flag is set to False, skipping request execution")
            self.logger.info(
                f"Payload: {json.dumps(agenzia.payload, indent=4)}")

    def execute_request(self, agenzia):
        website = self.session.query(Website).filter(
            Website.url.like(f"{self.base_uri}%")).first()
        response = self.reuest_handler.execute_request(
            self.agid, agenzia.payload, HEADERS)
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


def run_scraper(agid, execute, confirm, use_ai):
    logger.info(f"Running scraper for agid: {agid}")
    scraper = Scrapper(agid, execute, confirm, use_ai)
    scraper.run()
    del scraper
    return agid

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='839')
    parser.add_argument('--execute', help='execute request, default is False',
                        default=False, action='store_true')
    parser.add_argument('--confirm', help='confirm request execution',
                        default=True, action='store_true')
    parser.add_argument('--debug', help='debug mode',
                        default=False, action='store_true')
    parser.add_argument('--use-ai', help='use AI to extrapolate data',
                        default=False, action='store_true')
    parser.add_argument('--multiple', help='multiple agencies',
                        default=False, action='store_true')
    parser.add_argument('--max-parallelism', help='max parallelism', default=2, type=int)
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.multiple:
        with open('agids.txt', 'r') as data:
            numbers = [int(re.search(r'\[(\d+)\]', item).group(1))
                    for item in data if re.search(r'\[(\d+)\]', item)]
            agids = list(set(numbers))

        # Configura il numero di processi in parallelo (es. 4)
        max_parallelism = args.max_parallelism  # Puoi cambiare questo valore tra 2 e 4 come desideri

        # Esegui gli scraper in parallelo
        with concurrent.futures.ProcessPoolExecutor(max_parallelism) as executor:
            for agid in executor.map(run_scraper, agids, [args.execute]*len(agids), [args.confirm]*len(agids), [args.use_ai]*len(agids)):
                # Rimuovi l'agid processato dal file
                with open('agids.txt', 'r') as file:
                    lines = file.readlines()

                with open('agids.txt', 'w') as file:
                    for line in lines:
                        if f"[{agid}]" not in line:
                            file.write(line)
    else:
        scraper = Scrapper(args.agid, args.execute, args.confirm)
        scraper.run()
