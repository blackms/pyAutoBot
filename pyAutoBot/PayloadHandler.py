from .DataExtractor import DataExtractor
import re


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
        self.logger.info(
            f"Creating base payload for url: {data_dict['url']}")

        data_extractor = DataExtractor(self.logger)
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