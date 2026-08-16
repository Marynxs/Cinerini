"""Sobe a API para desenvolvimento, recusando começar se a porta estiver suja.

    python dev.py            porta 8000
    python dev.py --port 8080

Existe por um problema concreto: `uvicorn --reload` cria um processo filho que
herda o socket. Se o processo pai é encerrado à força, o filho sobrevive e
continua atendendo. Depois de algumas execuções, vários servidores dividem a
mesma porta — cada um com uma versão diferente do código em memória — e as
respostas passam a alternar entre eles.

O sintoma é enganoso: o código no disco está certo, mas a API responde com o
contrato antigo, e reiniciar "o" servidor não resolve porque não é um só.

Este script tenta reservar a porta antes de subir. Se ela já estiver ocupada,
para e diz o que fazer, em vez de somar mais um servidor à confusão.
"""

import argparse
import socket
import subprocess
import sys


def porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Sem SO_REUSEADDR de propósito: aqui o objetivo é justamente falhar
        # quando alguém já está escutando, e não conviver com o vizinho.
        try:
            s.bind(("127.0.0.1", porta))
            return True
        except OSError:
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true",
                        help="Recarrega ao salvar. Encerre com Ctrl+C, nunca "
                             "matando o processo, para não deixar filho órfão.")
    args = parser.parse_args()

    if not porta_livre(args.port):
        print(f"A porta {args.port} já está ocupada.\n")
        print("Provavelmente é um servidor de execução anterior que não foi")
        print("encerrado corretamente. Para achar e derrubar:\n")
        print(f"  PowerShell:  Get-NetTCPConnection -LocalPort {args.port} "
              "-State Listen |")
        print("                 Select-Object -ExpandProperty OwningProcess "
              "-Unique |")
        print("                 ForEach-Object { Stop-Process -Id $_ -Force }\n")
        print("Confira também processos filhos que sobreviveram ao pai:\n")
        print("  Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" |")
        print("    Where-Object { $_.CommandLine -match 'multiprocessing' }")
        return 1

    comando = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--port", str(args.port),
    ]
    if args.reload:
        comando.append("--reload")

    print(f"Subindo em http://127.0.0.1:{args.port}  (Ctrl+C para encerrar)")
    return subprocess.call(comando)


if __name__ == "__main__":
    sys.exit(main())
