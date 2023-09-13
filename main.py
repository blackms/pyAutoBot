import requests
import argparse
import logging
import json
import openai
import re
import regex
import colorlog
from urllib.parse import urlparse
from pyAutoBot import DBHandler, Website
from config import HEADERS, SITE_URL
from bs4 import BeautifulSoup
from pyAutoBot.agenzie import Gabetti, Remax, Toscano, Generica, Tecnorete
from pyAutoBot.data_extraction import DataExtraction
from secret import OPENAI_API_KEY
from validate_email import validate_email

# Setup logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

openai.api_key = OPENAI_API_KEY


class Utility:
    @staticmethod
    def get_base_uri(url):
        parsed_uri = urlparse(url)
        base_uri = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return base_uri.rstrip('/')

    # Other utility methods can be added here
    @staticmethod
    def clean_email(email):
        # Remove invalid characters
        email = regex.sub(r"[^a-zA-Z0-9._%+-@]", "", email)
        
        # Correct common TLD mistakes
        email = regex.sub(r"\.con\b", ".com", email)
        
        # Remove characters after TLD
        email = regex.sub(r"(\.[a-zA-Z]{2,4})[a-zA-Z]*$", r"\1", email)
        
        return email


class RequestHandler:
    @staticmethod
    def execute_request(agid, data_payload, headers):
        complete_url = f"{SITE_URL}/agenzia-mod-do.php?agid={agid}"
        # logger.info(f"Executing request to {complete_url} with payload: {json.dumps(data_payload, indent=4)}")
        logger.warning(f"Executing request to {complete_url}")
        response = requests.post(
            complete_url, data=data_payload, headers=headers)
        logger.info(
            f"Response received from {complete_url}: {response.status_code}")
        return response

    @staticmethod
    def _load_agency_from_site(url):
        logger.critical(f"Loading agency from site: {url}")

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

        # Extract input values into a dictionary
        data_dict = {
            inp.get('id'): inp.get('value', '')
            for inp in soup.find_all('input')
            if inp.get('id')
        }

        logger.debug(f"Extracted data: {json.dumps(data_dict, indent=4)}")
        return data_dict


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
        self.logger.warning(
            f"Creating base payload for url: {data_dict['url']}")
        self.logger.info(
            f"We don't know how to handle this agency, let's try to extrapolate data...")

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


class AgencyValidator:
    @staticmethod
    def is_valid_email(email):
        # Basic validation
        is_valid = validate_email(email)
        
        # Check if the domain of the email exists
        domain_exists = validate_email(email, check_mx=True)
        
        # Check if the email is accepted by the domain
        email_accepted = validate_email(email, verify=True)
        
        return is_valid and domain_exists and email_accepted

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

        return True, "All checks passed."


class Scrapper:
    def __init__(self, agid: int, execute: bool, confirm: bool, use_ai: bool = False):
        self.logger = logger.getChild(self.__class__.__name__)
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self.data_extractor = DataExtraction(self.logger)
        self._data_dict = RequestHandler._load_agency_from_site(
            f"{SITE_URL}/agenzia-mod.php?agid={self.agid}")
        self.payload_handler = PayloadHandler(self.logger)
        self.url = self._data_dict['url']
        self.confirm = confirm
        self.use_ai = use_ai
        with open('comuni.json', 'r') as data:
            self.comuni = json.load(data)

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
        # We don't have this agency in our classes, use generic one and try extrapolate data
        self.logger.info(
            f"We don't have this agency in our classes, use generic one and try extrapolate data...")
        agenzia = Generica(url, logger=self.logger, use_AI=self.use_ai)

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

        agenzia.payload['nomeente'] = self.extract_name_from_text(agenzia)
        self.get_agency_name_confirmation(agenzia)

        # try to extrapolate the description
        try:
            ex_data = self.data_extractor.try_to_extrapolate_data(
                agenzia.payload['url'])
            self.logger.warning(f"Extrapolated data: {ex_data}")
            chi_siamo = ex_data['chisiamo']
        except openai.error.RateLimitError:
            self.logger.error(f"Rate limit reached, manual input...")
            agenzia.payload['chisiamo'] = ''
            pass

        # try to clean mail
        email = Utility.clean_email(ex_data['email'])
        is_valid = AgencyValidator.is_valid_email(email)
        if self.confirm and not is_valid: exit(f"Invalid email: {email}")
        
        if not is_valid:
            self.logger.warning(f"Invalid email: {email}")
            email = input("Insert email: ")

        agenzia.payload['chisiamo'] = chi_siamo.encode(
            'latin-1', errors='ignore').decode('unicode_escape')
        agenzia.payload['email'] = email
        agenzia.payload['noemail'] = 'Y' if agenzia.payload['email'] == '' else 'N'
        for i in range(2, 3):
            agenzia.payload[f'localita{i}'] = ""
            agenzia.payload[f'localitacartella{i}'] = ""
            agenzia.payload[f'localitaprovincia{i}'] = ""

        # Uso delle funzioni
        locations = self.extract_locations_from_text(agenzia)
        if locations:
            self.logger.info(f"Found locations in the text: {locations}")
            self.add_location_to_payload(agenzia, locations)

        if 'Mi dispiace' in agenzia.payload['chisiamo'] or agenzia.payload['chisiamo'] == '':
            # failed to retrieve data from AI
            self.logger.warning(
                f"Failed retrieving description via AI, manual input...")
            self.logger.error(
                f"Error retrieving data from openai, manual input...")
            agenzia.payload['chisiamo'] = input("Insert description: ")
        if agenzia.is_agenzia_vacanze():
            agenzia.payload['isaffittituristici'] = 'Y'

        if self.confirm:
            is_valid, message = AgencyValidator.validate_agency_data(
                agenzia.payload)
            if is_valid is False:
                exit(f"Invalid agency data: {message}")

        return agenzia

    def extract_name_from_text(self, agenzia):
        if not agenzia.soup:
            self.logger.error("agenzia.soup is None.")
            return None
        
        text = agenzia.soup.get_text(separator=' ', strip=True)
        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": "Estrai e restituisci solo il nome dell'agenzia immobiliare preceduto da Agenzia Immobiliare dal seguente testo:" + text}
        ]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
        except openai.error.InvalidRequestError:
            self.logger.error(f"Cannot retrieve agency name from AI.")
            return None
        found_name = response['choices'][0]['message']['content'].strip()
        if isinstance(found_name, str):
            return found_name
        if isinstance(found_name, dict):
            # Se il risultato è un dizionario, prendi i suoi valori
            found_name = list(found_name.values())
        else:
            # Altrimenti, assegna direttamente il risultato
            found_name = found_name

    def extract_locations_from_text(self, agenzia):
        text = agenzia.soup.get_text(separator=' ', strip=True)
        messages = [
            {"role": "system", "content": "Sei un assistente virtuale che lavora per un'agenzia immobiliare."},
            {"role": "user", "content": "Estrai e restituisci solo la lista delle città in formato JSON dal seguente testo:" + text}
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            found_locations = response['choices'][0]['message']['content'].strip()
            self.logger.info(f"Found location: {found_locations}")

            if 'Mi dispiace' in found_locations:
                self.logger.warning(f"Failed retrieving locations via AI. Using parser method")
                return []

            loaded_data = json.loads(found_locations)
            if isinstance(loaded_data, dict):
                found_locations = list(loaded_data.values())
            else:
                found_locations = loaded_data

            self.logger.info(f"Found location: {found_locations}")

            flat_locations = [item for sublist in found_locations for item in sublist]
            locations = [self._find_city(location) for location in flat_locations if location]

        except openai.error.InvalidRequestError:
            self.logger.error(f"Cannot retrieve properties locations from AI. Using parser method")
            locations = self.try_get_locations(agenzia.payload['url'])

        # Filtra eventuali valori None dalla lista prima di restituirla
        return [location for location in locations if location]


    def add_location_to_payload(self, agenzia, locations):
        filters = ['napoli', 'canna']
        existing_locations = [agenzia.payload.get(
            f'localita{i}') for i in range(1, 4)]

        for location in locations:
            if location['nome'] not in filters and location['nome'] not in existing_locations:
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
            f"We have the agency in our classes, use the class to extrapolate data...")
        self.logger.warning(
            f"We already know how to handle this agency: {agenzia.payload['nomeente']}, using the description from the class...")
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
        response = RequestHandler.execute_request(
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


# The main execution code remains the same
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='476')
    parser.add_argument('--execute', help='execute request, default is False',
                        default=False, action='store_true')
    parser.add_argument('--confirm', help='confirm request execution',
                        default=False, action='store_true')
    parser.add_argument('--debug', help='debug mode',
                        default=False, action='store_true')
    parser.add_argument('--use-ai', help='use AI to extrapolate data',
                        default=False, action='store_true')
    parser.add_argument('--multiple', help='multiple agencies',
                        default=False, action='store_true')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.multiple:
        with open('agids.txt', 'r') as data:
            numbers = [int(re.search(r'\[(\d+)\]', item).group(1))
                       for item in data if re.search(r'\[(\d+)\]', item)]
            agids = list(set(numbers))
            logger.info(f"Agids: {','.join(map(str, sorted(agids)))}")

    else:
        scraper = Scrapper(args.agid, args.execute, args.confirm)
        scraper.run()
