from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, Organizer
from app.models import Role, User
from app.ratelimit import login_by_account, rate_limit
from app.schemas import LoginIn, PromoteIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    # Folgado de propósito: escritório, universidade e operadora móvel põem
    # muita gente atrás de um IP só. Apertar aqui puniria usuário legítimo
    # sem impedir quem distribui a varredura entre vários endereços.
    dependencies=[Depends(rate_limit(limit=20, window_seconds=3600, scope="register"))],
)
def register(data: RegisterIn, db: DbSession) -> TokenOut:
    """Cadastro público. Cria CUSTOMER — exceto na instalação vazia.

    O papel nunca vem do corpo da requisição: aceitá-lo deixaria qualquer
    visitante se declarar organizador e decidir quem entra na sala. Portaria
    é criada pelo organizador, e organizador é promovido por outro (D22).

    A resposta de e-mail duplicado revela que a conta existe. Ver decisão D8:
    esconder isso exigiria confirmação por e-mail, fora do escopo. O limite
    acima é a mitigação — cinco tentativas por hora inviabilizam varrer uma
    lista de e-mails atrás de quem tem conta.
    """
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    # Banco sem ninguém: o primeiro a se cadastrar vira organizador, senão a
    # instalação nasce sem caminho para o primeiro (D22). A condição é a
    # tabela estritamente vazia, e não "não há organizador" — assim a regra
    # se fecha no primeiro cadastro e nunca reabre, nem se um organizador
    # for removido depois.
    vazio = db.scalar(select(User.id).limit(1)) is None
    papel = Role.ORGANIZER if vazio else Role.CUSTOMER

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=papel,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenOut,
    # Mesma razão do cadastro: a defesa contra força bruta de senha é a
    # janela por conta, logo abaixo. Esta só corta volume anormal de rede.
    dependencies=[Depends(rate_limit(limit=60, window_seconds=300, scope="login"))],
)
def login(data: LoginIn, db: DbSession) -> TokenOut:
    conta = data.email.lower()

    # Limite por conta além do limite por IP: um atacante com muitos IPs
    # testaria senhas da mesma conta sem nunca esbarrar no limite de rede.
    espera = login_by_account.check(conta)
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas para esta conta. Aguarde alguns minutos.",
            headers={"Retry-After": str(espera)},
        )

    user = db.scalar(select(User).where(User.email == data.email))

    # Mesma resposta para e-mail inexistente e senha errada: distinguir os
    # dois permitiria descobrir quais e-mails têm conta no sistema.
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    # Acerto zera a contagem: quem sabe a senha não deve ser punido por ter
    # errado antes, e sem isso um erro de digitação travaria o dono da conta.
    login_by_account.reset(conta)

    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get(
    "/organizers",
    response_model=list[UserOut],
    tags=["organizador"],
    summary="Quem já é organizador",
)
def list_organizers(db: DbSession, _: Organizer) -> list[UserOut]:
    return [
        UserOut.model_validate(u) for u in db.scalars(
            select(User).where(User.role == Role.ORGANIZER).order_by(User.name)
        )
    ]


@router.post(
    "/organizers",
    response_model=UserOut,
    tags=["organizador"],
    summary="Promove uma conta existente a organizador",
)
def promote_organizer(
    data: PromoteIn, db: DbSession, promotor: Organizer
) -> UserOut:
    """Promoção em vez de criação: a conta e a senha já são da pessoa.

    Criar a conta pelo painel obrigaria o organizador a inventar uma senha e
    entregá-la por algum canal — e senha que trafega por mensagem é senha
    que fica no histórico de alguém. Aqui a conta já existe, e o que se
    concede é só o papel (D22).

    Funcionário é promovível: quem trabalha na casa é justamente quem se
    espera promover. O que muda é que ele deixa de ser funcionário —
    acumular os dois papéis daria a quem opera a porta o poder de publicar e
    cancelar sessões.
    """
    alvo = db.scalar(select(User).where(User.email == data.email))

    if alvo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nenhuma conta com este e-mail. Peça que se cadastre primeiro.",
        )

    if alvo.role == Role.ORGANIZER:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta conta já é de organizador.")

    # Funcionário promovido deixa de ser funcionário: os papéis são
    # exclusivos, e quem passa a publicar não continua validando na porta.
    # Se precisar dos dois, são duas contas — e aí fica registrado que são
    # duas pessoas diferentes na mesma sessão.
    alvo.gate_venue_id = None
    alvo.gate_showing_id = None
    alvo.role = Role.ORGANIZER
    db.commit()
    db.refresh(alvo)

    return UserOut.model_validate(alvo)
