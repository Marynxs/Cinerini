from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # Assina sessões e ingressos com HS256, que exige chave de pelo menos o
    # tamanho do hash (RFC 7518, 3.2). Recusada na subida, e não avisada na
    # primeira assinatura: chave curta torna o QR forjável por força bruta.
    secret_key: str = Field(min_length=32)
    tmdb_api_key: str = ""
    cors_origins: str = "http://localhost:5173"

    # Janela em que o assento fica reservado durante o checkout.
    hold_minutes: int = 10

    # Validade do token de sessão do usuário. O código do ingresso não expira:
    # quem valida é a portaria, e a fonte de verdade sobre uso é o banco.
    access_token_hours: int = 12

    # Só ligar quando houver um proxy confiável à frente reescrevendo
    # X-Forwarded-For. Ligado sem proxy, qualquer cliente forja o próprio IP
    # e escapa do limite de tentativas.
    trust_proxy: bool = False

    # Teto geral por IP, em todas as rotas. Folgado: uma navegação normal faz
    # dezenas por minuto, e escritório ou operadora móvel põem muita gente
    # atrás de um IP só. Existe para cortar volume de robô, não para medir uso.
    requests_per_minute: int = 300

    # Uma linha JSON por requisição, para o CloudWatch. Desligado no
    # desenvolvimento, onde o log de texto do uvicorn se lê melhor.
    log_json: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
