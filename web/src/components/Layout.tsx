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

export function Carregando({ texto = 'Carregando' }: { texto?: string }) {
  return (
    <div className="aviso-tela">
      <span className="carregando">{texto}</span>
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
