import argparse
import concurrent.futures
import json
import logging
import re
import time
import threading
from urllib.parse import urlparse

import colorlog
import openai
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from ratelimiter import RateLimiter


from config import HEADERS, SITE_URL
from pyAutoBot import DBHandler, Website
from pyAutoBot.Agenzie import Gabetti, Generica, Remax, Tecnorete, Toscano
from pyAutoBot.DataExtractor import DataExtractor
from pyAutoBot.PayloadHandler import PayloadHandler
from pyAutoBot.RequestHandler import RequestHandler
from pyAutoBot.AgencyValidator import AgencyValidator
from pyAutoBot.Utility import Utility
from secret import OPENAI_API_KEY

rate_limiter = RateLimiter(max_calls=15, period=60)  # 10 richieste al minuto

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

# Leggi il file una sola volta all'inizio
with open('agids.txt', 'r') as file:
    lines = file.readlines()


class AutoBot:
    def __init__(self, agid: int, execute: bool, confirm: bool, use_ai: bool = False):
        self.logger = logger.getChild(self.__class__.__name__)
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self.request_handler = RequestHandler(self.logger)
        self._data_dict = self.request_handler.load_agency_from_site(
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

    def get_agenzia_instance(self, data: json, nomeente: str, url: str) -> object:
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
                    data, url, logger=self.logger, use_AI=self.use_ai)
                nomeente = agenzia.get_name()
                break

        return agenzia

    def get_agency_name_confirmation(self, agenzia):
        if self.confirm:
            if not agenzia.payload['nomeente']:
                logger.error("Cannot retrieve agency name from AI.")
                self.request_handler.put_agency_under_review(agenzia)
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

    def handle_unknown_agency(self, url: str):
        agenzia = Generica(self._data_dict, url,
                           logger=self.logger, use_AI=self.use_ai)

        agenzia.try_extract_name()
        self.get_agency_name_confirmation(agenzia)

        extrapolated_data = agenzia.try_load_chi_siamo()
        if extrapolated_data is None:
            # must be handled manually
            self.logger.error("Error retrieving data from AI.")
            self.logger.info("Moving agency in to_review.")
            self.request_handler.put_agency_under_review(self, "Error retrieving data from AI.")
            return None

        # try to clean mail
        email = Utility.clean_email(agenzia.extrapolated_data['email'])
        validator = AgencyValidator(self.logger)
        is_valid = validator.is_valid_email(email)
        chi_siamo = re.sub(
            r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), extrapolated_data['chisiamo'])

        agenzia.payload['email'] = "" if not is_valid else email
        agenzia.payload['noemail'] = 'Y' if agenzia.payload['email'] == '' else 'N'

        self.logger.info("Trying to extract description from text...")
        try:
            agenzia.chisiamo = chi_siamo
        except Exception as e:
            self.logger.error(f"Error: {e}")
            agenzia.payload['chisiamo'] = chi_siamo

        for i in range(2, 3):
            setattr(agenzia, f'localita{i}', '')

        try:
            locations = self.data_extractor.try_extract_locations_from_text(
                agenzia)
        except openai.error.InvalidRequestError:
            self.logger.error(
                f"Cannot retrieve properties locations from AI. Using parser method")
            locations = agenzia.try_get_locations(agenzia.payload['url'])

        if locations:
            self.logger.info(f"Found locations in the text: {locations}")
            self.add_location_to_payload(agenzia, locations)

        if agenzia.is_agenzia_vacanze():
            agenzia.payload['isaffittituristici'] = 'Y'

        if agenzia.payload['telefonostandard'] == '':
            try:
                agenzia.payload['telefonostandard'] = self.data_extractor.try_parse_phone_number(
                    agenzia)
            except:
                self.logger.error("Error retrieving phone number from AI.")

        if self.confirm:
            validator = AgencyValidator(self.logger)
            is_valid, message = validator.validate_agency_data(agenzia.payload)
            self.logger.debug(f"Is valid: {is_valid}, message: {message}")
            if is_valid is False:
                self.logger.debug(json.dumps(agenzia.payload, indent=4))
                self.logger.critical(f"Invalid agency data: {message}")
                # put agency under review
                self.request_handler.put_agency_under_review(agenzia, message)
                return None

        return agenzia

    @rate_limiter
    def geocode_address(self, address):
        try:
            return self.geolocator.geocode(address)
        except GeocoderUnavailable:
            time.sleep(5)  # Aspetta 10 secondi prima di riprovare
            return self.geolocator.geocode(address)

    def get_distance_between_provinces(self, province1, province2):
        location1 = self.geocode_address(f"{province1}, Italy")
        location2 = self.geocode_address(f"{province2}, Italy")

        if location1 and location2:
            distance = geodesic((location1.latitude, location1.longitude),
                                (location2.latitude, location2.longitude)).km
            return distance
        return float('inf')

    def add_location_to_payload(self, agenzia, locations):
        self.logger.info(
            f"Found multiple locations. Locations to process: {len(locations)}")
        filters = ['napoli', 'canna']
        existing_locations = [agenzia.payload.get(
            f'localita{i}') for i in range(1, 4)]
        primary_province = agenzia.payload['localita1']

        for location in locations:
            # Se sia localita2 che localita3 sono valorizzate, interrompi il ciclo
            if agenzia.payload['localita2'] and agenzia.payload['localita3']:
                break

            distance = self.get_distance_between_provinces(
                primary_province, location['sigla'])
            if location['nome'] not in filters and location['nome'] not in existing_locations and distance <= 50:
                index = None
                if not agenzia.payload['localita2']:
                    index = '2'
                elif not agenzia.payload['localita3']:
                    index = '3'

                if index:
                    agenzia.payload[f'localita{index}'] = location['nome']
                    agenzia.payload[f'localitacartella{index}'] = location['nome'].lower(
                    )
                    agenzia.payload[f'localitaprovincia{index}'] = location['sigla']

    def handle_known_agency(self, agenzia):
        self.logger.info(
            f"We already know how to handle this agency: {agenzia.payload['nomeente']}, using the description from the class...")

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

    

    def execute_request(self, agenzia):
        website = self.session.query(Website).filter(
            Website.url.like(f"{self.base_uri}%")).first()
        response = self.request_handler.execute_request(
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

        agenzia = self.get_agenzia_instance(self._data_dict, nomeente, url)
        if agenzia is None:
            agenzia = self.handle_unknown_agency(url)
        else:
            agenzia = self.handle_known_agency(agenzia)
            
        if agenzia is None:
            self.logger.error("Agency not valid.")
        else:
            self.logger.debug(json.dumps(agenzia.payload, indent=4))
            self.execute_request(agenzia)


def process_agid(agid, execute, confirm, use_ai):
    # Esegui la tua funzione scraper
    run_scraper(agid, execute, confirm, use_ai)


def run_scraper(agid, execute, confirm, use_ai):
    logger.info(f"Running scraper for agid: {agid}")
    scraper = AutoBot(agid, execute, confirm, use_ai)
    scraper.run()
    del scraper
    return agid


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='2233')
    parser.add_argument('--execute', help='execute request, default is False',
                        default=True, action='store_true')
    parser.add_argument('--confirm', help='confirm request execution',
                        default=True, action='store_true')
    parser.add_argument('--debug', help='debug mode',
                        default=False, action='store_true')
    parser.add_argument('--use-ai', help='use AI to extrapolate data',
                        default=False, action='store_true')
    parser.add_argument('--multiple', help='multiple agencies',
                        default=False, action='store_true')
    parser.add_argument('--max-parallelism',
                        help='max parallelism', default=2, type=int)
    args = parser.parse_args()

    # Leggi il file una sola volta all'inizio
    with open('agids.txt', 'r') as file:
        lines = file.readlines()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.multiple:
        with open('agids.txt', 'r') as data:
            numbers = [int(re.search(r'\[(\d+)\]', item).group(1))
                       for item in data if re.search(r'\[(\d+)\]', item)]
            agids = list(set(numbers))

        # Configura il numero di processi in parallelo (es. 4)
        # Puoi cambiare questo valore tra 2 e 4 come desideri
        max_parallelism = args.max_parallelism

        # Esegui gli scraper in parallelo
        with concurrent.futures.ProcessPoolExecutor(max_parallelism) as executor:
            executor.map(process_agid, agids, [
                         args.execute]*len(agids), [args.confirm]*len(agids), [args.use_ai]*len(agids))

    else:
        scraper = AutoBot(args.agid, args.execute, args.confirm)
        scraper.run()
