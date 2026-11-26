"""Linha de log por requisição, consumida pelo painel do CloudWatch."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.request_log import JsonFormatter


def _registros(caplog: pytest.LogCaptureFixture) -> list[dict]:
    return [r.fields for r in caplog.records if r.name == "cinerini.request"]


def test_registra_o_modelo_da_rota_e_nao_o_caminho(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """O painel agrupa por rota; o caminho com ID espalharia um valor por evento."""
    with caplog.at_level(logging.INFO, logger="cinerini.request"):
        client.get("/events/987654")

    [registro] = _registros(caplog)
    assert registro["route"] == "/events/{event_id}"
    assert registro["status"] == 404
    assert registro["method"] == "GET"
    assert registro["duration_ms"] >= 0


def test_caminho_sem_rota_vira_rotulo_fixo(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="cinerini.request"):
        client.get("/wp-admin/setup.php")

    [registro] = _registros(caplog)
    assert registro["route"] == "sem-rota"


def test_health_nao_e_registrado(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Verificado a cada poucos segundos: seria a maior parte do volume."""
    with caplog.at_level(logging.INFO, logger="cinerini.request"):
        client.get("/health")

    assert _registros(caplog) == []


def test_formato_e_json_com_os_campos_no_topo() -> None:
    """Campos no topo, e não aninhados, para o Logs Insights lê-los direto."""
    record = logging.LogRecord("cinerini.request", logging.INFO, "", 0, "request", None, None)
    record.fields = {"route": "/health", "status": 200}

    linha = json.loads(JsonFormatter().format(record))

    assert linha["route"] == "/health"
    assert linha["status"] == 200
    assert linha["level"] == "INFO"
