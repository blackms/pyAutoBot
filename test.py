import spacy
import re

# Carica il modello italiano di spaCy
nlp = spacy.load("it_core_news_sm")

# Testo da analizzare
testo = """
San Siro Servizi Immobiliari è un'agenzia immobiliare con sede legale in Pavia, Italia. 
Offrono servizi immobiliari sia per la vendita che per l'affitto di proprietà. 
La sede operativa si trova in Via Mascheroni n° 26 a Pavia. 
L'agenzia è registrata presso il Registro delle Imprese di Pavia con il numero di partita IVA e codice fiscale 02097660183. 
Possono essere contattati tramite telefono al numero 0382/538158, tramite fax al numero 0382/1850800, 
e tramite email all'indirizzo info@sansiroimmobiliare.it. 
Hanno anche una pagina Facebook e un account Twitter per contatti e informazioni aggiuntive.
"""

# Processa il testo con spaCy
doc = nlp(testo)

# Estrai entità nominate
for ent in doc.ents:
    print(ent.text, ent.label_)

# Estrai indirizzo email con regex
email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,3}"
emails = re.findall(email_pattern, testo)
print("Email:", emails)

# Estrai numeri di telefono con regex (questo è un esempio semplice e potrebbe non coprire tutti i casi)
phone_pattern = r"\d{4}/\d{6}"
phones = re.findall(phone_pattern, testo)
print("Telefoni:", phones)