"""Refaz o ambiente de demonstração todo dia.

As contas de teste são públicas, de propósito: quem avalia o projeto entra
como organizador e pode apagar o que quiser. Em vez de restringir o que a
conta faz, o estado volta ao do seed a cada madrugada, com as sessões
recalculadas a partir do dia, que de outro modo venceriam em três semanas.

Chamada pelo EventBridge Scheduler. Não fala com o banco: manda a própria
instância da API rodar o seed por SSM, com a imagem e as credenciais que já
estão lá. Assim a função não precisa de VPC, driver de Postgres nem senha.
"""

import os
import time

import boto3

ssm = boto3.client("ssm")
ec2 = boto3.client("ec2")

COMANDO = (
    "cd /opt/cinerini && "
    "docker compose -f docker-compose.prod.yml run --rm api python -m app.seed --reset"
)
PENDENTES = {"Pending", "InProgress", "Delayed"}


def handler(event, context):
    reservas = ec2.describe_instances(Filters=[
        {"Name": "tag:Project", "Values": [os.environ["PROJECT"]]},
        {"Name": "instance-state-name", "Values": ["running"]},
    ])["Reservations"]
    if not reservas:
        raise RuntimeError("Nenhuma instância do projeto em execução.")
    instancia = reservas[0]["Instances"][0]["InstanceId"]

    comando = ssm.send_command(
        InstanceIds=[instancia],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [COMANDO]},
        Comment="reset diario do ambiente de demonstracao",
    )["Command"]["CommandId"]

    # Espera o resultado para que uma falha vire erro da função, e o erro
    # dispare o alarme. Sem esperar, a função terminaria com sucesso sempre.
    status, inv = "Pending", {}
    for _ in range(30):
        time.sleep(5)
        try:
            inv = ssm.get_command_invocation(CommandId=comando, InstanceId=instancia)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        status = inv["Status"]
        if status not in PENDENTES:
            break

    if status != "Success":
        raise RuntimeError(f"Seed terminou como {status}: {inv.get('StandardErrorContent', '')[-1000:]}")

    return {"instancia": instancia, "saida": inv["StandardOutputContent"][-1000:]}
