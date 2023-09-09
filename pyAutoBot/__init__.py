from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Website(Base):
    __tablename__ = 'websites'
    id = Column(Integer, Sequence('website_id_seq'), primary_key=True)
    url = Column(String)
    nomeente = Column(String)
    telefonostandard = Column(String)
    email = Column(String)
    noemail = Column(String)
    indirizzo = Column(String)
    cap = Column(String)
    localita = Column(String)
    localitacartella = Column(String)
    zona = Column(String)
    provincia = Column(String)
    isagenzia = Column(String)
    isaffittituristici = Column(String)
    localita1 = Column(String)
    localitaprovincia1 = Column(String)
    localitacartella1 = Column(String)
    localita2 = Column(String)
    localitaprovincia2 = Column(String)
    localitacartella2 = Column(String)
    localita3 = Column(String)
    localitaprovincia3 = Column(String)
    localitacartella3 = Column(String)
    chisiamo = Column(String(2000))
    note = Column(String)
    agid = Column(String)
    azione = Column(String)

class DBHandler:
    def __init__(self):
        self.engine = create_engine('sqlite:///data.db')
        self.Session = sessionmaker(bind=self.engine)
        
    def init_db(self):
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        return self.Session()