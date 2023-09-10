# pyAutoBot

## Descrizione

`pyAutoBot` è un progetto Python focalizzato sull'estrazione di informazioni dalle pagine web delle agenzie immobiliari e sulla loro memorizzazione in un database. Il progetto utilizza librerie come BeautifulSoup per il parsing del contenuto HTML e OpenAI per l'elaborazione e la generalizzazione delle descrizioni.

## Funzionalità principali

1. **Estrazione di informazioni**: Il progetto può estrarre vari dettagli come email, descrizione e lista di immobili dalle pagine web delle agenzie immobiliari.
2. **Supporto per diverse agenzie**: Il codice supporta diverse agenzie immobiliari come Generica, Gabetti, Remax e Toscano.
3. **Utilizzo di OpenAI**: Per generalizzare le descrizioni e ottenere dettagli rilevanti, il progetto utilizza OpenAI.

## Struttura del codice

- **__init__.py**: Definizione del modello del database e gestione delle operazioni del database.
- **agenzie.py**: Contiene classi per diverse agenzie immobiliari e metodi per estrarre informazioni.
- **data_extraction.py**: Utilizza OpenAI per estrarre e generalizzare le descrizioni.

## Come iniziare

1. Clona il repository: `git clone https://github.com/blackms/pyAutoBot.git`
2. Installa le dipendenze: `pip install -r requirements.txt`
3. Esegui il file principale: `python main.py`

## Contribuire

Se desideri contribuire al progetto, sentiti libero di fare una pull request o aprire un issue sul [repository GitHub](https://github.com/blackms/pyAutoBot).

---

Per ulteriori dettagli o domande, contatta il maintainer del progetto o consulta la documentazione ufficiale.