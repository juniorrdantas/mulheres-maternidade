
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base


class Participante(Base):
    __tablename__ = "participantes"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação da participante
    nome = Column(String(150), nullable=False)
    idade = Column(Integer)

    # Campos da pesquisa antiga - preservados
    profissao = Column(String(150), nullable=True)
    escolaridade = Column(String(100), nullable=True)
    tem_filhos = Column(String(10), nullable=True)
    quantidade_filhos = Column(Integer, nullable=True)

    # Campos da nova pesquisa
    situacao_trabalho = Column(String(150), nullable=True)
    dificuldade_trabalho = Column(Text, nullable=True)
    preocupacao_profissional = Column(Text, nullable=True)
    conhecimento_direitos = Column(Text, nullable=True)
    suporte_cras = Column(Text, nullable=True)
    sofreu_discriminacao = Column(String(10), nullable=True)
    relato = Column(Text, nullable=True)

    # Data do cadastro
    data_cadastro = Column(DateTime, default=datetime.now)
