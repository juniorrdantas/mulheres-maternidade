from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class Participante(Base):
    __tablename__ = "participantes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    idade = Column(Integer)
    profissao = Column(String(150))
    escolaridade = Column(String(100))
    tem_filhos = Column(String(10))
    quantidade_filhos = Column(Integer)
    situacao_trabalho = Column(String(100))
    sofreu_discriminacao = Column(String(10))
    relato = Column(Text)
    data_cadastro = Column(DateTime, default=datetime.now)