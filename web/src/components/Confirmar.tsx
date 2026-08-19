/* Confirmação de ação destrutiva.
   Sobre o <dialog> nativo e não sobre uma <div> com posição fixa: ele já
   traz camada superior, prisão de foco, fechamento pelo Esc e restauração
   do foco ao elemento que abriu: quatro coisas que uma div exigiria
   reimplementar, cada uma com um jeito de sair errada. */

import { useEffect, useRef, useState } from 'react';
import './Confirmar.css';

interface Props {
  titulo: string;
  /** Corpo da confirmação: o que exatamente vai acontecer. */
  children: React.ReactNode;
  rotuloConfirmar: string;
  /** Presente quando a ação exige justificativa escrita. */
  motivo?: { rotulo: string; sugestao?: string };
  aoConfirmar: (motivo: string) => void;
  aoFechar: () => void;
}

export function Confirmar({
  titulo, children, rotuloConfirmar, motivo, aoConfirmar, aoFechar,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [texto, setTexto] = useState('');

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  const faltaMotivo = Boolean(motivo) && texto.trim().length === 0;

  return (
    <dialog ref={ref} className="dialogo" onCancel={aoFechar} onClose={aoFechar}>
      <form
        method="dialog"
        className="dialogo-papel"
        onSubmit={(e) => {
          e.preventDefault();
          if (faltaMotivo) return;
          aoConfirmar(texto.trim());
        }}
      >
        <p className="dialogo-etiqueta">Confirmação</p>
        <h2 className="dialogo-titulo">{titulo}</h2>

        <div className="dialogo-picote" />

        <div className="dialogo-corpo">{children}</div>

        {motivo && (
          <label className="dialogo-campo">
            <span className="campo-rotulo">{motivo.rotulo}</span>
            <input
              type="text"
              value={texto}
              maxLength={255}
              placeholder={motivo.sugestao}
              onChange={(e) => setTexto(e.target.value)}
              autoFocus
            />
          </label>
        )}

        <div className="dialogo-picote" />

        <div className="dialogo-acoes">
          <button
            type="button"
            className="botao-compacto botao-compacto--vazado"
            onClick={() => ref.current?.close()}
          >
            Voltar
          </button>
          <button
            type="submit"
            className="botao-compacto botao-compacto--carimbo"
            disabled={faltaMotivo}
          >
            {rotuloConfirmar}
          </button>
        </div>
      </form>
    </dialog>
  );
}
