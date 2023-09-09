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

# Setup logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

logger = colorlog.getLogger(__name__)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

openai.api_key = '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'


class Scrapper:
    def __init__(self, agid: int, execute: bool):
        self.agid = agid
        self.db_handler = DBHandler()
        self.execute = execute
        self._data_dict = self._load_agency_from_site(f"{SITE_URL}/agenzia-mod.php?agid={self.agid}")
        self.url = self._data_dict['url']

    def get_base_uri(self, url):
        parsed_uri = urlparse(url)
        base_uri = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return base_uri.rstrip('/')
    
    def execute_request(self, data_payload, headers):
        complete_url = f"{SITE_URL}/agenzia-mod-do.php?agid={self.agid}"
        logger.info(f"Executing request to {complete_url} with payload: {json.dumps(data_payload, indent=4)}")
        response = requests.post(complete_url, data=data_payload, headers=headers)
        logger.info(f"Response received from {complete_url}: {response.status_code}")
        return response
    
    def strip_name(self, name: str) -> str:
        pass
    
    def try_to_extrapolate_data(self, url: str) -> dict:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Use the OpenAI Completion API to process the "Who We Are" section
        text_content = soup.get_text(separator=' ', strip=True)
        logger.debug(f"Text content: {text_content}")
        # Define a regular expression pattern for typical email formats
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"
    
        # Search the entire webpage content for emails
        try:
            emails = re.findall(email_pattern, soup.get_text())[0]
        except IndexError:
            logger.error(f"Email not found, setting default to info...")
            # extrapolate the domain for the url
            domain = urlparse(url).netloc
            emails = f"info@{domain}"
        logger.info(f"Emails: {emails}")
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
            logger.error(f"Text is too lomg, insert manually...")
            summary = input("Insert summary: ")
            return {'chisiamo': summary, 'email': emails}

        # Extract the assistant's response from the reply
        summary = response['choices'][0]['message']['content'].strip()
        return {'chisiamo': summary, 'email': emails}
    
    def _load_agency_from_site(self, url: str) -> dict:
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
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
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
        
    
    def create_base_payload(self) -> dict:
        logger.info(f"Creating base payload for url: {self._data_dict['url']}")

        data_dict = self._data_dict
        
        # Extrapolate data with AI
        ex_data = self.try_to_extrapolate_data(data_dict['url'])
        logger.info(f"Extrapolated data: {ex_data}")
        chi_siamo = ex_data['chisiamo']
        email = ex_data['email']
        
        base_payload = BASE_PAYLOAD
        base_payload['url'] = data_dict['url']
        # clear a little of shit
        pattern = "(Agenzia Immobiliare Tempocasa).*"
        data_dict['nomeente'] = re.sub(pattern, r'\1', data_dict['nomeente'])
        if 'Agenzia Immobiliare' not in data_dict['nomeente']:
            base_payload['nomeente'] = f"Agenzia Immobiliare {data_dict['nomeente']}"
        else:
            base_payload['nomeente'] = data_dict['nomeente']
        base_payload['telefonostandard'] = f"{data_dict['telefonostandard']}"
        base_payload['indirizzo'] = data_dict['indirizzo']
        base_payload['cap'] = data_dict['cap']
        base_payload['localita'] = data_dict['localita0']
        base_payload['localitacartella'] = data_dict['localitacartella0'].lower()
        base_payload['provincia'] = data_dict['localitaprovincia0']
        base_payload['agid'] = self.agid
        base_payload['chisiamo'] = chi_siamo.encode('latin-1').decode('unicode_escape')
        base_payload['email'] = email
        return base_payload

    def run(self):
        base_uri = self.get_base_uri(self.url)
        self.db_handler.init_db()
        session = self.db_handler.get_session()
        base_uri = base_uri.rstrip('/')
        website = session.query(Website).filter(Website.url.like(f"{base_uri}%")).first()
        
        # if base_uri is present in websites nomeent column, then load the payload from the database
        if website is not None:
            logger.info(f"Loading payload from database for base_uri: {base_uri}")
            data_payload = {column.name: getattr(website, column.name) for column in Website.__table__.columns if column.name != "id"}
        else:
            logger.warning(f"We don't have this base_uri in our database: {base_uri}, we try to load the informations...")
            logger.warning(f"")
            data_payload = self.create_base_payload()
            # localita1, localitaprovincia1 and localitacartella1 will be the same as localita and localitacartella
            data_payload['localita1'] = data_payload['localita']
            data_payload['localitaprovincia1'] = data_payload['provincia']
            data_payload['localitacartella1'] = data_payload['localitacartella']
            data_payload['noemail'] = 'Y' if data_payload['email'] == '' else 'N'
            
            
        if self.execute:
            logger.info(f"Payload: {json.dumps(data_payload, indent=4)}")
            while True:
                user_input = input("Do you want to continue? (Y/N): ")
                if user_input in ['Y', 'N', 'y', 'n']:
                    if user_input == 'N':
                        logger.info(f"Exiting...")
                        exit(0)
                    break
                else:
                    print("Invalid input. Please enter 'Y' or 'N'.")
            response = self.execute_request(data_payload, HEADERS)
            if response.status_code == 200:
                logger.info(f"Request executed successfully")
                # save payload to database
                logger.info(f"Saving payload to database")
                website = Website(**data_payload)
                session.add(website)
                session.commit()
                logger.info(f"Payload saved to database")
        else:
            logger.info(f"Execute flag is set to False, skipping request execution")
            logger.info(f"Payload: {json.dumps(data_payload, indent=4)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agid', help='agid', default='167')
    parser.add_argument('--execute', help='execute request, default is False', default=False, action='store_true')
    parser.add_argument('--debug', help='debug mode', default=False, action='store_true')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)

    scraper = Scrapper(args.agid, args.execute)
    scraper.run()