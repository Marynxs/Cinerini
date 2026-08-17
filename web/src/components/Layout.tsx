import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

import { useAuth } from '../auth/AuthContext';
import './Layout.css';

interface Props {
  children: ReactNode;
  /** Telas que gerenciam a própria altura, como o mapa de assentos. */
  semPadding?: boolean;
}

export function Layout({ children, semPadding }: Props) {
  const { user, sair } = useAuth();

  return (
    <div className="casca">
      <header className="topo">
        <div className="topo-conteudo">
          <Link to="/" className="topo-marca">Cinerini</Link>

          <div className="topo-acoes">
            {user ? (
              <>
                <span className="topo-usuario">{user.name}</span>
                {user.role === 'customer' && (
                  <Link to="/meus-ingressos" className="elo">
                    Meus ingressos
                  </Link>
                )}
                {user.role === 'organizer' && (
                  <Link to="/painel" className="elo">Painel</Link>
                )}
                <button type="button" className="elo elo--fraco" onClick={sair}>
                  Sair
                </button>
              </>
            ) : (
              <Link to="/entrar" className="elo">Entrar</Link>
            )}
          </div>
        </div>
      </header>

      {semPadding ? children : <main className="conteudo">{children}</main>}
    </div>
  );
}

/** Retorno explícito para a tela anterior.

    O botão do navegador existe, mas não é visível dentro da página — e num
    fluxo de compra a pessoa precisa ver que dá para recuar sem perder o que
    já escolheu. */
export function Voltar({ para, texto }: { para: string; texto: string }) {
  return (
    <Link to={para} className="voltar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
           aria-hidden="true">
        <path d="M15 5l-7 7 7 7" />
      </svg>
      {texto}
    </Link>
  );
}

/* Depois de quantos segundos a espera deixa de parecer normal e passa a
   parecer defeito. Abaixo disso o aviso só assustaria quem ia ser atendido
   em seguida. */
const ESPERA_LONGA_MS = 4000;

export function Carregando({ texto = 'Carregando' }: { texto?: string }) {
  const [demorando, setDemorando] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDemorando(true), ESPERA_LONGA_MS);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="aviso-tela">
      <span className="carregando">{texto}</span>

      {/* Terceira camada contra a hibernação do plano gratuito, depois do
          aquecimento no front e do ping agendado. As duas primeiras encurtam
          a espera; esta trata a que sobrar — dizer o motivo é o que separa
          "está lento" de "está quebrado". */}
      {demorando && (
        <p className="aviso-demora">
          O servidor gratuito hiberna quando fica sem uso. Religar leva até
          um minuto, e só na primeira visita.
        </p>
      )}
    </div>
  );
}

export function Vazio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="aviso-tela">
      <p className="aviso-tela-titulo">{titulo}</p>
      {children}
    </div>
  );
}
