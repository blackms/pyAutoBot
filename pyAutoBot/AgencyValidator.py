from validate_email import validate_email
import re


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
        
        return True if is_valid and domain_exists else False

    def validate_agency_data(self, data):
        # Controlla che url, nomeente, telefonostandard non siano vuoti
        if not data.get('url') or not data.get('nomeente') or not data.get('telefonostandard'):
            return False, "[ERROR] Mancano i dati dell'agenzia di base (presa da Ultimo Minuto). Controllare manualmente."
        
        if 'Mi dispiace' in data.get('nomeente'):
            return False, "[ERROR] Non e' stato possibile estrapolare il nome dell'agenzia. Controllare manualmente."

        # Valida l'email
        if not self.is_valid_email(data.get('email')):
            return False, "[EMAIL] [WARN] Email non trovata o non ha superato i filtri antispam, controllare manualmente."

        # Controlla che noemail sia impostato su 'N'
        if data.get('noemail') != 'N':
            return False, "[WARN] Il campo noemail non è impostato su 'N'. Controllare manualmente se effettivamente l'agenzia non ha un indirizzo email."

        # Controlla che indirizzo, cap, localita, localitacartella non siano vuoti
        if not data.get('indirizzo') or not data.get('cap') or not data.get('localita') or not data.get('localitacartella'):
            return False, "[ERROR] Mancano i dati dell'indirizzo. Controllare manualmente."

        # Controlla che provincia non sia vuoto
        if not data.get('provincia'):
            return False, "[ERROR] Manca la provincia. Controllare manualmente."

        # Controlla che localita1, localitaprovincia1, localitacartella1 non siano vuoti
        if not data.get('localita1') or not data.get('localitaprovincia1') or not data.get('localitacartella1'):
            return False, "[ERROR] Mancano i dati della località 1 (ovvero dove opera l'agenzia). Controllare manualmente."

        # Controlla che chisiamo non sia vuoto e contenga testo
        if not data.get('chisiamo') or not data['chisiamo'].strip():
            return False, "[ERROR] Impossibile estrapolare la descrizione dell'agenzia. Controllare manualmente."
        
        if 'Error retrieving data.' in data.get('chisiamo'):
            return False, "[ERROR] Impossibile estrapolare la descrizione dell'agenzia. Controllare manualmente."
        
        if 'Facebook' in data.get('nomeente'):
            return False, "[Facebook] [WARN] Controllo manuale del nome via sito."
        
        if 'Mi dispiace' in data.get('chisiamo'):
            return False, "[ERROR] Impossibile estrapolare la descrizione dell'agenzia. Controllare manualmente."
        
        # if RE/MAX or RE / MAX or RE/MAX Italia or RE/MAX Italia S.p.A. in nomeente using a regexp
        # if 're/max' in data.get('nomeente').lower() or 're / max' in data.get('nomeente').lower() or 're/max italia' in data.get('nomeente').lower() or 're/max italia s.p.a.' in data.get('nomeente').lower(): 
        #    return False, "[RE/MAX] [SOFTWARN] Controllo manuale del nome via sito."
        
        # if 'Gobetti' in data.get('nomeente'):
        #    return False, "[Gabetti] [SOFTWARN] Controllo manuale del nome via sito."
        
        # if 'Tempocasa' in data.get('nomeente'):
        #    return False, "[Tempocasa] [SOFTWARN] Controllo manuale del nome via sito."
        
        # if len(data.get('nomeente')) < 5 or len(data.get('nomeente')) > 30:
        #    return False, "[WARN] Il nome risulta o troppo corto o troppo lungo. Perfavore controllare manualmente."
        
        # if (data.get('isaffittituristici') == 'Y'):
        #    return False, "[SOFTWARN] L'agenzia è segnata come affitti turistici (breve periodo). Perfavore controllare manualmente."
        
        if 'Mi dispiace' in data.get('nomeente'):
            return False, '[ERROR] Impossibile recuperare il nome dell\'agenzia. Controllare manualmente.'
        
        if 'powered by' in data.get('nomeente').lower():
            return False, '[ERROR] Impossibile recuperare il nome dell\'agenzia. Controllare manualmente.'
        
        #if 'Tecnocasa' in data.get('nomeente'):
        #    return False, '[Tecnocasa] [SOFTWARN] Controllo manuale del nome dell\'agenzia.'
        
        # se il nome e' composto da una parola sola, meglio mandare in revisione
        #if len(data.get('nomeente').split()) == 1:
        #    return False, "[WARN] Il nome dell'agenzia e' composto da una sola parola. Perfavore controllare manualmente."

        return True, "All checks passed."
    
    
class Reviewer():
    def __init__(self, logger):
        self.logger = logger.getChild(__name__)
        self.validator = AgencyValidator(logger)
        
    def validate_agency(self, agenzia):
        data = agenzia.payload
        is_valid, message = self.validator.validate_agency_data(data)
        if not is_valid:
            self.logger.warning(f"Agency {data.get('nomeente')} is not valid: {message}")
            return False
        return True
        
    def run():
        pass
    
    