import copy


def decode_text(text):
        # Puoi aggiungere altre codifiche se necessario
        #encodings = ['utf-8', 'latin1', 'iso-8859-1']
        encodings = ['iso-8859-1']
        for encoding in encodings:
            try:
                return text.encode(encoding).decode('utf-8')
            except UnicodeDecodeError:
                continue
        return text

class AgenziaBase:
    def __init__(self, data, logger):
        self.payload = {}
        self.logger = logger.getChild(__name__)

        # Crea una copia profonda del dizionario
        data_copy = copy.deepcopy(data)

        # Rimuove le chiavi che non servono
        data_copy.pop('isagenziaY', None)
        data_copy.pop('isagenziaN', None)
        data_copy.pop('isaffittituristiciY', None)
        data_copy.pop('isaffittituristiciN', None)
        data_copy.pop('name', None)

        # Applica le trasformazioni specificate
        data_copy['localita'] = data_copy.pop('localita0', None)
        data_copy['localitacartella'] = data_copy.pop(
            'localitacartella0', '').lower()
        data_copy['provincia'] = data_copy.pop('localitaprovincia0', None)

        for key, value in data_copy.items():
            setattr(self, key, value)
            setattr(self, f"_{key}", value)

        self.localita1 = data_copy.pop('localita', '')
        self.localitaprovincia1 = data_copy.pop('provincia', '')
        self.localitacartella1 = data_copy.pop(
            'localitacartella', '').lower()
        
        self._note = ''
        self._chisiamo = ''
        self._nourl = 'N'
        self._isaffittituristici = ''
        self._isagenzia = ''
        
        # Set Default
        self.isaffittituristici = 'N'
        self.isagenzia = 'Y'


    @property
    def url(self):
        return self._url

    @url.getter
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.payload['url'] = value

    @property
    def nomeente(self):
        return self._nomeente

    @nomeente.setter
    def nomeente(self, value):
        # normalize the name of the agency to be all lowercase except for the first letter of each word
        value = value.lower()
        value = value.title()
        self._nomeente = value
        self.payload['nomeente'] = value

    @property
    def telefonostandard(self):
        return self._telefonostandard

    @telefonostandard.setter
    def telefonostandard(self, value):
        self._telefonostandard = value
        self.payload['telefonostandard'] = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        self._email = value
        self.payload['email'] = value

    @property
    def noemail(self):
        return self._noemail

    @noemail.setter
    def noemail(self, value):
        self._noemail = value
        self.payload['noemail'] = value

    @property
    def indirizzo(self):
        return self._indirizzo

    @indirizzo.setter
    def indirizzo(self, value):
        self._indirizzo = value
        self.payload['indirizzo'] = value

    @property
    def cap(self):
        return self._cap

    @cap.setter
    def cap(self, value):
        self._cap = value
        self.payload['cap'] = value

    @property
    def localita(self):
        return self._localita

    @localita.setter
    def localita(self, value):
        self._localita = value
        self.payload['localita'] = value

    @property
    def localitacartella(self):
        return self._localitacartella

    @localitacartella.setter
    def localitacartella(self, value):
        self._localitacartella = value
        self.payload['localitacartella'] = value

    @property
    def zona(self):
        return self._zona

    @zona.setter
    def zona(self, value):
        self._zona = value
        self.payload['zona'] = value

    @property
    def provincia(self):
        return self._provincia

    @provincia.setter
    def provincia(self, value):
        self._provincia = value
        self.payload['provincia'] = value

    @property
    def isagenzia(self):
        return self._isagenzia

    @isagenzia.setter
    def isagenzia(self, value):
        self._isagenzia = value
        self.payload['isagenzia'] = value

    @property
    def isaffittituristici(self):
        return self._isaffittituristici

    @isaffittituristici.setter
    def isaffittituristici(self, value):
        self._isaffittituristici = value
        self.payload['isaffittituristici'] = value

    @property
    def localita1(self):
        return self._localita1

    @localita1.setter
    def localita1(self, value):
        self._localita1 = value
        self.payload['localita1'] = value

    @property
    def localitaprovincia1(self):
        return self._localitaprovincia1

    @localitaprovincia1.setter
    def localitaprovincia1(self, value):
        self._localitaprovincia1 = value
        self.payload['localitaprovincia1'] = value

    @property
    def localitacartella1(self):
        return self._localitacartella1

    @localitacartella1.setter
    def localitacartella1(self, value):
        self._localitacartella1 = value
        self.payload['localitacartella1'] = value

    @property
    def localita2(self):
        return self._localita2

    @localita2.setter
    def localita2(self, value):
        self._localita2 = value
        self.payload['localita2'] = value

    @property
    def localitaprovincia2(self):
        return self._localitaprovincia2

    @localitaprovincia2.setter
    def localitaprovincia2(self, value):
        self._localitaprovincia2 = value
        self.payload['localitaprovincia2'] = value

    @property
    def localitacartella2(self):
        return self._localitacartella2

    @localitacartella2.setter
    def localitacartella2(self, value):
        self._localitacartella2 = value
        self.payload['localitacartella2'] = value

    @property
    def localita3(self):
        return self._localita3

    @localita3.setter
    def localita3(self, value):
        self._localita3 = value
        self.payload['localita3'] = value

    @property
    def localitaprovincia3(self):
        return self._localitaprovincia3

    @localitaprovincia3.setter
    def localitaprovincia3(self, value):
        self._localitaprovincia3 = value
        self.payload['localitaprovincia3'] = value

    @property
    def localitacartella3(self):
        return self._localitacartella3

    @localitacartella3.setter
    def localitacartella3(self, value):
        self._localitacartella3 = value
        self.payload['localitacartella3'] = value

    @property
    def chisiamo(self):
        return self._chisiamo

    @chisiamo.setter
    def chisiamo(self, value):
        value = decode_text(value)
        self._chisiamo = value
        self.payload['chisiamo'] = value

    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, value):
        self._note = value
        self.payload['note'] = value

    @property
    def agid(self):
        return self._agid

    @agid.setter
    def agid(self, value):
        self._agid = value
        self.payload['agid'] = value

    @property
    def azione(self):
        return self._azione

    @azione.setter
    def azione(self, value):
        self._azione = value
        self.payload['azione'] = value
