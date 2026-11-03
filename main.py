
import os
import secrets
from collections import Counter
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine, SessionLocal
from models import Participante


# --------------------------------------------------
# CONFIGURAÇÕES
# --------------------------------------------------

load_dotenv(override=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mulheres, Maternidade e Mercado de Trabalho"
)


# Verifica a chave de sessão
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET não encontrada no arquivo .env"
    )


# Configuração das sessões
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False
)


# Arquivos estáticos e templates
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")


# --------------------------------------------------
# BANCO DE DADOS
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# AUTENTICAÇÃO E EXPIRAÇÃO DE SESSÃO
# --------------------------------------------------

def administrador_logado(request: Request):

    expiracao = request.session.get("expiracao")

    if not expiracao:
        request.session.clear()
        return False

    agora = datetime.now().timestamp()

    if agora >= expiracao:
        request.session.clear()
        return False

    return request.session.get("admin_logado") is True


# --------------------------------------------------
# PÁGINA INICIAL
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# --------------------------------------------------
# RECEBIMENTO DAS RESPOSTAS DO QUESTIONÁRIO
# --------------------------------------------------

@app.post("/responder")
def responder(
    nome: str = Form(...),
    idade: int = Form(...),
    profissao: str = Form(...),
    escolaridade: str = Form(...),
    tem_filhos: str = Form(...),
    quantidade_filhos: int = Form(0),
    sofreu_discriminacao: str = Form(...),
    relato: str = Form(""),
    db: Session = Depends(get_db)
):

    participante = Participante(
        nome=nome,
        idade=idade,
        profissao=profissao,
        escolaridade=escolaridade,
        tem_filhos=tem_filhos,
        quantidade_filhos=quantidade_filhos,
        situacao_trabalho="",
        sofreu_discriminacao=sofreu_discriminacao,
        relato=relato
    )

    db.add(participante)
    db.commit()

    return RedirectResponse(
        "/obrigado",
        status_code=303
    )


# --------------------------------------------------
# PÁGINA DE AGRADECIMENTO
# --------------------------------------------------

@app.get("/obrigado", response_class=HTMLResponse)
def obrigado(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="obrigado.html"
    )


# --------------------------------------------------
# TELA DE LOGIN
# --------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):

    if administrador_logado(request):
        return RedirectResponse(
            "/admin",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erro": None}
    )


# --------------------------------------------------
# AUTENTICAÇÃO DO ADMINISTRADOR
# --------------------------------------------------

@app.post("/login", response_class=HTMLResponse)
def realizar_login(
    request: Request,
    usuario: str = Form(...),
    senha: str = Form(...)
):

    usuario_correto = os.getenv("ADMIN_USERNAME")
    senha_correta = os.getenv("ADMIN_PASSWORD")

    # Verifica se as configurações existem
    if not usuario_correto or not senha_correta:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "erro": "Configuração administrativa não encontrada. Verifique o arquivo .env."
            },
            status_code=500
        )

    # Compara o usuário, permitindo caracteres acentuados
    usuario_valido = (
        usuario.strip() == usuario_correto.strip()
    )

    # Compara a senha de maneira segura
    senha_valida = secrets.compare_digest(
        senha.encode("utf-8"),
        senha_correta.encode("utf-8")
    )

    if usuario_valido and senha_valida:

        request.session.clear()

        request.session["admin_logado"] = True

        # Define a expiração fixa de 5 minutos
        request.session["expiracao"] = (
            datetime.now() + timedelta(minutes=5)
        ).timestamp()

        return RedirectResponse(
            "/admin",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "erro": "Usuário ou senha incorretos."
        },
        status_code=401
    )


# --------------------------------------------------
# ENCERRAR SESSÃO
# --------------------------------------------------

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/",
        status_code=303
    )


# --------------------------------------------------
# PAINEL ADMINISTRATIVO
# --------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin(
    request: Request,
    db: Session = Depends(get_db)
):

    # Verifica autenticação e prazo da sessão
    if not administrador_logado(request):
        return RedirectResponse(
            "/login",
            status_code=303
        )

    # Busca os participantes no banco
    participantes = db.query(Participante).order_by(
        Participante.data_cadastro.desc()
    ).all()

    # Total de participantes
    total = len(participantes)

    # Participantes que relataram discriminação
    discriminacao_sim = sum(
        1
        for p in participantes
        if (p.sofreu_discriminacao or "").strip().lower()
        in ["sim", "s", "true", "1"]
    )

    # Percentual de discriminação
    percentual_discriminacao = (
        round((discriminacao_sim / total) * 100, 1)
        if total else 0
    )

    # Estatísticas de escolaridade
    escolaridade = Counter(
        (p.escolaridade or "Não informado")
        for p in participantes
    )

    # Estatísticas de profissões
    profissoes = Counter(
        (p.profissao or "Não informado")
        for p in participantes
    )

    # Estatísticas de maternidade
    maternidade = Counter(
        (p.tem_filhos or "Não informado")
        for p in participantes
    )

    # Quantidade de filhos
    quantidade_filhos = Counter(
        str(p.quantidade_filhos or 0)
        for p in participantes
    )

    # Estatísticas de discriminação
    discriminacao = Counter(
        (p.sofreu_discriminacao or "Não informado")
        for p in participantes
    )

    # Renderiza o painel
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "participantes": participantes,
            "total": total,
            "discriminacao_sim": discriminacao_sim,
            "percentual_discriminacao": percentual_discriminacao,
            "escolaridade": escolaridade.most_common(),
            "profissoes": profissoes.most_common(),
            "maternidade": maternidade.most_common(),
            "quantidade_filhos": quantidade_filhos.most_common(),
            "discriminacao": discriminacao.most_common()
        }
    )
