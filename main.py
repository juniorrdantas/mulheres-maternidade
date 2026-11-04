
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

SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET não encontrada no arquivo .env"
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False
)

# --------------------------------------------------
# ARQUIVOS ESTÁTICOS
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# Disponibilização dos PDFs da apresentação e cartilha
app.mount(
    "/documentos",
    StaticFiles(directory="documentos"),
    name="documentos"
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
# MENSAGENS PERSONALIZADAS DE INCENTIVO
# --------------------------------------------------

def gerar_mensagem_incentivo(
    situacao_trabalho,
    dificuldade_trabalho,
    preocupacao_profissional,
    conhecimento_direitos,
    sofreu_discriminacao
):

    dificuldade = (dificuldade_trabalho or "").lower()
    preocupacao = (preocupacao_profissional or "").lower()
    conhecimento = (conhecimento_direitos or "").lower()
    discriminacao = (sofreu_discriminacao or "").lower()
    situacao = (situacao_trabalho or "").lower()

    # Situação de discriminação
    if (
        discriminacao.strip() == "sim"
        or "rejeição" in dificuldade
        or "pressão" in dificuldade
    ):
        return (
            "Você merece respeito e igualdade!",
            "Nenhuma mulher deve ser prejudicada profissionalmente "
            "por ser mãe. Sua experiência merece ser ouvida, seus "
            "direitos precisam ser respeitados e sua capacidade "
            "profissional não pode ser definida pela maternidade. "
            "Você merece trabalhar em um ambiente digno, justo e "
            "livre de discriminação."
        )

    # Situação de desemprego
    if "desempregada" in situacao:
        return (
            "Novas oportunidades podem surgir!",
            "Estar fora do mercado de trabalho não diminui seu "
            "talento, sua capacidade ou seu valor. Sua trajetória "
            "continua sendo importante. A maternidade faz parte "
            "da sua história, mas não limita seus sonhos nem suas "
            "possibilidades profissionais. Você merece oportunidades "
            "e condições justas para recomeçar."
        )

    # Dificuldade de conciliar trabalho e maternidade
    if (
        "conciliar" in preocupacao
        or "rotina de trabalho" in preocupacao
    ):
        return (
            "Você não precisa dar conta de tudo sozinha!",
            "Conciliar maternidade e trabalho pode ser desafiador. "
            "É importante lembrar que o cuidado com os filhos não "
            "deve ser uma responsabilidade enfrentada sem apoio. "
            "Você também merece tempo, oportunidades, reconhecimento "
            "e condições dignas para desenvolver sua vida profissional."
        )

    # Dificuldade com creche e rede de apoio
    if (
        "creche" in preocupacao
        or "deixar o bebê" in preocupacao
        or "rede de apoio" in preocupacao
    ):
        return (
            "Você merece apoio nessa caminhada!",
            "Ter uma rede de apoio e acesso a serviços de cuidado "
            "infantil pode fazer diferença na vida de uma mãe. "
            "Buscar apoio não é sinal de fraqueza. É um direito "
            "e uma necessidade legítima. Sua participação ajuda "
            "a dar visibilidade a essa realidade."
        )

    # Preocupação com renda
    if "renda" in preocupacao:
        return (
            "Seus sonhos e sua independência importam!",
            "A preocupação com a renda e o sustento da família "
            "é uma realidade para muitas mulheres. Você merece "
            "oportunidades de trabalho, valorização profissional "
            "e condições para construir um futuro com mais "
            "segurança e autonomia."
        )

    # Conhecimento dos direitos
    if (
        "dúvidas" in conhecimento
        or "não conheço" in conhecimento
    ):
        return (
            "Conhecer seus direitos é um passo importante!",
            "Toda mulher merece conhecer e ter respeitados seus "
            "direitos. Buscar informação é uma forma de fortalecer "
            "sua autonomia e reconhecer o valor da sua trajetória. "
            "Você não está sozinha nessa busca por respeito e "
            "igualdade de oportunidades."
        )

    # Mensagem geral
    return (
        "Sua voz importa e sua história tem valor!",
        "Sua participação contribui para ampliar o diálogo sobre "
        "maternidade, trabalho e igualdade de oportunidades. "
        "Cada experiência compartilhada ajuda a dar visibilidade "
        "aos desafios enfrentados pelas mulheres. Continue "
        "reconhecendo seu valor, sua capacidade e seus direitos. "
        "Você merece respeito e oportunidades."
    )


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
    request: Request,
    nome: str = Form(...),
    idade: int = Form(...),
    situacao_trabalho: str = Form(...),
    dificuldade_trabalho: str = Form(...),
    preocupacao_profissional: str = Form(...),
    conhecimento_direitos: str = Form(...),
    suporte_cras: str = Form(...),
    sofreu_discriminacao: str = Form(...),
    relato: str = Form(""),
    db: Session = Depends(get_db)
):

    participante = Participante(
        nome=nome.strip(),
        idade=idade,

        # Campos da pesquisa atual
        situacao_trabalho=situacao_trabalho,
        dificuldade_trabalho=dificuldade_trabalho,
        preocupacao_profissional=preocupacao_profissional,
        conhecimento_direitos=conhecimento_direitos,
        suporte_cras=suporte_cras,
        sofreu_discriminacao=sofreu_discriminacao,
        relato=relato.strip()
    )

    try:
        db.add(participante)
        db.commit()

    except Exception:
        db.rollback()
        raise

    # Gera a mensagem personalizada após o registro no banco
    titulo, mensagem = gerar_mensagem_incentivo(
        situacao_trabalho=situacao_trabalho,
        dificuldade_trabalho=dificuldade_trabalho,
        preocupacao_profissional=preocupacao_profissional,
        conhecimento_direitos=conhecimento_direitos,
        sofreu_discriminacao=sofreu_discriminacao
    )

    # Guarda somente a mensagem de agradecimento na sessão
    request.session["titulo_incentivo"] = titulo
    request.session["mensagem_incentivo"] = mensagem

    return RedirectResponse(
        "/obrigado",
        status_code=303
    )


# --------------------------------------------------
# PÁGINA DE AGRADECIMENTO PERSONALIZADO
# --------------------------------------------------

@app.get("/obrigado", response_class=HTMLResponse)
def obrigado(request: Request):

    titulo = request.session.pop(
        "titulo_incentivo",
        "Sua voz importa!"
    )

    mensagem = request.session.pop(
        "mensagem_incentivo",
        "Sua participação é muito importante. Cada experiência "
        "compartilhada contribui para fortalecer o debate sobre "
        "maternidade, igualdade de oportunidades e respeito às "
        "mulheres no mercado de trabalho."
    )

    return templates.TemplateResponse(
        request=request,
        name="obrigado.html",
        context={
            "titulo_incentivo": titulo,
            "mensagem_incentivo": mensagem
        }
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

    if not usuario_correto or not senha_correta:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "erro": "Configuração administrativa não encontrada. Verifique o arquivo .env."
            },
            status_code=500
        )

    usuario_valido = (
        usuario.strip() == usuario_correto.strip()
    )

    senha_valida = secrets.compare_digest(
        senha.encode("utf-8"),
        senha_correta.encode("utf-8")
    )

    if usuario_valido and senha_valida:

        request.session.clear()

        request.session["admin_logado"] = True

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

    if not administrador_logado(request):
        return RedirectResponse(
            "/login",
            status_code=303
        )

    participantes = db.query(Participante).order_by(
        Participante.data_cadastro.desc()
    ).all()

    total = len(participantes)

    # Discriminação profissional
    discriminacao_sim = sum(
        1
        for p in participantes
        if (p.sofreu_discriminacao or "").strip().lower()
        in ["sim", "s", "true", "1"]
    )

    percentual_discriminacao = (
        round((discriminacao_sim / total) * 100, 1)
        if total else 0
    )

    # Estatísticas da pesquisa atual
    situacao_trabalho = Counter(
        p.situacao_trabalho or "Não informado"
        for p in participantes
    )

    dificuldade_trabalho = Counter(
        p.dificuldade_trabalho or "Não informado"
        for p in participantes
    )

    preocupacao_profissional = Counter(
        p.preocupacao_profissional or "Não informado"
        for p in participantes
    )

    conhecimento_direitos = Counter(
        p.conhecimento_direitos or "Não informado"
        for p in participantes
    )

    suporte_cras = Counter(
        p.suporte_cras or "Não informado"
        for p in participantes
    )

    discriminacao = Counter(
        p.sofreu_discriminacao or "Não informado"
        for p in participantes
    )

    # Estatísticas antigas preservadas para compatibilidade
    escolaridade = Counter(
        p.escolaridade or "Não informado"
        for p in participantes
    )

    profissoes = Counter(
        p.profissao or "Não informado"
        for p in participantes
    )

    maternidade = Counter(
        p.tem_filhos or "Não informado"
        for p in participantes
    )

    quantidade_filhos = Counter(
        str(p.quantidade_filhos or 0)
        for p in participantes
    )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "participantes": participantes,
            "total": total,
            "discriminacao_sim": discriminacao_sim,
            "percentual_discriminacao": percentual_discriminacao,

            # Pesquisa atual
            "situacao_trabalho": situacao_trabalho.most_common(),
            "dificuldade_trabalho": dificuldade_trabalho.most_common(),
            "preocupacao_profissional": preocupacao_profissional.most_common(),
            "conhecimento_direitos": conhecimento_direitos.most_common(),
            "suporte_cras": suporte_cras.most_common(),

            # Compatibilidade com o painel antigo
            "escolaridade": escolaridade.most_common(),
            "profissoes": profissoes.most_common(),
            "maternidade": maternidade.most_common(),
            "quantidade_filhos": quantidade_filhos.most_common(),
            "discriminacao": discriminacao.most_common()
        }
    )
