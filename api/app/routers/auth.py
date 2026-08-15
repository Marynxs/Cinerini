from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Role, User
from app.ratelimit import login_by_account, rate_limit
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
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
    """Cadastro público. Cria sempre CUSTOMER.

    Organizador e portaria não se auto-cadastram: são criados pelo seed ou
    pelo organizador. Aceitar o papel vindo do corpo da requisição deixaria
    qualquer visitante virar organizador.

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

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.CUSTOMER,
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
