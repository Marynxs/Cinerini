import { Fragment } from 'react';

import './Stepper.css';

export type Etapa = 'poltronas' | 'pagamento' | 'confirmacao';

const ORDEM: Etapa[] = ['poltronas', 'pagamento', 'confirmacao'];

const ROTULOS: Record<Etapa, string> = {
  poltronas: 'Escolha suas poltronas',
  pagamento: 'Escolha sua forma de pagamento',
  confirmacao: 'Confirmação',
};

/* Ícones em traço, sem preenchimento: acompanham a cor do disco em cada
   estado sem precisar de variante por cor. */

function IconePoltrona() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 11V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v5" />
      <path d="M4 11h16v6H4z" />
      <path d="M6 17v3M18 17v3" />
    </svg>
  );
}

function IconePagamento() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2.5" y="5.5" width="19" height="13" rx="1.5" />
      <path d="M2.5 10h19" />
      <path d="M6 14.5h4" />
    </svg>
  );
}

function IconeConfirmacao() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5l2.8 2.8L16 9.5" />
    </svg>
  );
}

const ICONES: Record<Etapa, () => React.ReactElement> = {
  poltronas: IconePoltrona,
  pagamento: IconePagamento,
  confirmacao: IconeConfirmacao,
};

interface Props {
  atual: Etapa;
}

export function Stepper({ atual }: Props) {
  const indiceAtual = ORDEM.indexOf(atual);

  return (
    <nav className="trilha" aria-label="Etapas da compra">
      {ORDEM.map((etapa, indice) => {
        const feita = indice < indiceAtual;
        const eAtual = indice === indiceAtual;
        const Icone = ICONES[etapa];

        const classes = [
          'trilha-etapa',
          feita && 'trilha-etapa--feita',
          eAtual && 'trilha-etapa--atual',
        ].filter(Boolean).join(' ');

        return (
          <Fragment key={etapa}>
            {indice > 0 && (
              <span
                className={`trilha-filete${feita || eAtual ? ' trilha-filete--feito' : ''}`}
                aria-hidden="true"
              />
            )}

            <div className={classes} aria-current={eAtual ? 'step' : undefined}>
              <span className="trilha-disco">
                <Icone />
              </span>
              <span className="trilha-rotulo">{ROTULOS[etapa]}</span>
            </div>
          </Fragment>
        );
      })}
    </nav>
  );
}
