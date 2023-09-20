import json

import requests
from bs4 import BeautifulSoup

from config import SITE_URL


class RequestHandler:
    def __init__(self, logger):
        self.logger = logger.getChild(__name__)
        self.headers = {
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
        
    def execute_request(self, agid, data_payload, headers):
        data_payload['azione'] = 'Salva'
        complete_url = f"{SITE_URL}/agenzia-mod-do.php?agid={agid}"
        self.logger.warning(f"Executing request to {complete_url}")
        response = requests.post(
            complete_url, data=data_payload, headers=self.headers)
        self.logger.info(
            f"Response received from {complete_url}: {response.status_code}")
        return response

    def load_agency_from_site(self, url):
        self.logger.info(f"Loading agency from site: {url}")
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract input values into a dictionary
        data_dict = {
            inp.get('id'): inp.get('value', '')
            for inp in soup.find_all('input')
            if inp.get('id')
        }

        # self.logger.debug(f"Extracted data: {json.dumps(data_dict, indent=4)}")
        return data_dict
    
    def put_agency_under_review(self, agenzia, url='https://www.ultimissimominuto.com/editors/agenzia-mod-do.php'):
        agenzia.payload['azione'] = 'Rivedi'
        response = requests.post(url, headers=self.headers, data=agenzia.payload)
        self.logger.info(f"Response received from {url}: {response.status_code}")
        return response.text