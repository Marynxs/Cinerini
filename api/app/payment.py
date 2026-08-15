"""Cobrança simulada.

Sem transação financeira real, conforme o enunciado. O desfecho é
determinístico e não aleatório: o avaliador precisa conseguir demonstrar
aprovação e recusa quando quiser, não quando a sorte permitir.
"""

import re
from dataclasses import dataclass

# Cartão terminado neste dígito é recusado. Documentado no README para que
# ambos os caminhos sejam percorríveis.
DIGITO_RECUSA = "0"


@dataclass(frozen=True)
class Charge:
    approved: bool
    reason: str | None = None


def only_digits(card_number: str) -> str:
    return re.sub(r"\D", "", card_number)


def charge(card_number: str, amount_cents: int) -> Charge:
    """O valor não influencia o desfecho; entra na assinatura porque um
    provedor real o exigiria, e trocar a simulação por um de verdade não
    deve mudar quem chama."""
    numero = only_digits(card_number)

    if len(numero) < 13 or len(numero) > 19:
        return Charge(False, "Número de cartão inválido.")

    if numero.endswith(DIGITO_RECUSA):
        return Charge(False, "Pagamento recusado pela operadora.")

    return Charge(True)
