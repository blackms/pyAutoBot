from validate_email import validate_email


class AgencyValidator:
    def __init__(self, logger):
        self.logger = logger.getChild(__name__)
    
    def is_valid_email(self, email):
        # Basic validation
        is_valid = validate_email(email)
        
        # Check if the domain of the email exists
        domain_exists = validate_email(email, check_mx=True)
        
        # Check if the email is accepted by the domain
        email_accepted = validate_email(email, verify=True)
        self.logger.info(f"Email: {email}, is_valid: {is_valid}, domain_exists: {domain_exists}, email_accepted: {email_accepted}")
        
        return is_valid

    def validate_agency_data(self, data):
        # Controlla che url, nomeente, telefonostandard non siano vuoti
        if not data.get('url') or not data.get('nomeente') or not data.get('telefonostandard'):
            return False, "URL, nomeente, or telefonostandard is empty."
        
        if 'Mi dispiace' in data.get('nomeente'):
            return False, "Nomeente contains 'Mi dispiace'."

        # Valida l'email tramite regex
        if not self.is_valid_email(data.get('email')):
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