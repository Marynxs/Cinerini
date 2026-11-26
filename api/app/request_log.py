"""Uma linha JSON por requisição, consultável no CloudWatch Logs Insights.

Ligado só com LOG_JSON=true. O log de acesso do uvicorn é texto livre e não
traz duração: para calcular p95 ou taxa de erro seria preciso extrair campos
com expressão regular a cada consulta.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone

from fastapi import Request, Response

from app.ratelimit import client_ip

logger = logging.getLogger("cinerini.request")

# Rotas que respondem a verificações automáticas a cada poucos segundos.
# Registradas, seriam a maior parte do volume e do custo de ingestão sem
# dizer nada que a métrica de saúde já não diga.
SILENCIOSAS = {"/health"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_json_logging() -> None:
    """Troca a saída dos loggers da aplicação e do uvicorn por JSON.

    Chamado depois de o uvicorn configurar os próprios loggers, e por isso
    prevalece sobre a configuração dele. O log de acesso do uvicorn sai: a
    linha deste módulo o substitui com mais campos.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("cinerini", "uvicorn", "uvicorn.error"):
        log = logging.getLogger(name)
        log.handlers = [handler]
        log.propagate = False
        log.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True


async def log_request(request: Request, call_next) -> Response:
    inicio = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # O modelo da rota, e não o caminho: `/events/{event_id}` agrupa todas
        # as consultas a evento num valor só. Caminho que não casou com rota
        # nenhuma vira um rótulo fixo, para que varredura de robô não espalhe
        # milhares de valores distintos.
        rota = request.scope.get("route")
        modelo = getattr(rota, "path", None) or "sem-rota"
        if modelo not in SILENCIOSAS:
            logger.info("request", extra={"fields": {
                "method": request.method,
                "route": modelo,
                "status": status,
                "duration_ms": round((time.perf_counter() - inicio) * 1000, 1),
                "client": client_ip(request),
            }})
