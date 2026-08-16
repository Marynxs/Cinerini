import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';

import { compartilhamento, compra } from '../api/endpoints';
import type { MyTicket } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Confirmar } from '../components/Confirmar';
import { Carregando, Layout, Vazio, Voltar } from '../components/Layout';
import './MyTickets.css';

const dinheiro = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
  });

const quando = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(',', '');

export function MyTickets() {
  const { user, carregando: carregandoSessao } = useAuth();
  const navegar = useNavigate();

  const [ingressos, setIngressos] = useState<MyTicket[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (carregandoSessao) return;

    if (!user) {
      navegar('/entrar', { state: { de: '/meus-ingressos' }, replace: true });
      return;
    }

    compra.meusIngressos()
      .then(setIngressos)
      .catch((e: Error) => setErro(e.message));
  }, [carregandoSessao, navegar, user]);

  if (erro) {
    return (
      <Layout>
        <Vazio titulo="Não deu para carregar seus ingressos">
          <p>{erro}</p>
        </Vazio>
      </Layout>
    );
  }

  if (!ingressos) {
    return <Layout><Carregando texto="Buscando seus ingressos" /></Layout>;
  }

  return (
    <Layout>
      <Voltar para="/" texto="Catálogo" />

      <div className="catalogo-cabeca">
        <h1 className="catalogo-titulo">Meus ingressos</h1>
        <span className="catalogo-contagem">
          {ingressos.length} {ingressos.length === 1 ? 'ingresso' : 'ingressos'}
        </span>
      </div>

      {ingressos.length === 0 ? (
        <Vazio titulo="Você ainda não tem ingressos">
          <p>Escolha uma sessão no catálogo para comprar o primeiro.</p>
          <p style={{ marginTop: 'var(--e4)' }}>
            <Link to="/" className="elo">Ver o que está em cartaz</Link>
          </p>
        </Vazio>
      ) : (
        <div className="ingressos">
          {ingressos.map((ingresso) => (
            <Bilhete key={ingresso.id} ingresso={ingresso}
                     aoMudar={setIngressos} />
          ))}
        </div>
      )}
    </Layout>
  );
}

function Bilhete({ ingresso, aoMudar }: {
  ingresso: MyTicket; aoMudar: (lista: MyTicket[]) => void;
}) {
  const [link, setLink] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const usado = ingresso.status === 'used';
  const cancelado = ingresso.status === 'cancelled';
  const ativo = !usado && !cancelado;

  async function compartilhar() {
    setGerando(true);
    try {
      const criado = await compartilhamento.criar(ingresso.id);
      setLink(`${window.location.origin}/ingresso/${criado.token}`);
    } finally {
      setGerando(false);
    }
  }

  async function cancelar() {
    setCancelando(true);
    setErro(null);
    try {
      aoMudar(await compra.cancelarIngresso(ingresso.id));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCancelando(false);
    }
  }

  async function copiar() {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  return (
    <article className={`bilhete${usado ? ' bilhete--usado' : ''}${
      cancelado ? ' bilhete--cancelado' : ''}`}
    >
      <div className="bilhete-corpo">
        {ingresso.poster_url && (
          <img
            className="bilhete-poster"
            src={ingresso.poster_url}
            alt=""
            loading="lazy"
          />
        )}

        <div>
          <h2 className="bilhete-titulo">{ingresso.event_title}</h2>

          <dl className="bilhete-linhas">
            <div className="bilhete-linha">
              <dt>Poltrona</dt>
              <dd className="bilhete-poltrona">{ingresso.seat_label}</dd>
            </div>
            <div className="bilhete-linha">
              <dt>Quando</dt>
              <dd>{quando(ingresso.starts_at)}</dd>
            </div>
            <div className="bilhete-linha">
              <dt>Cinema</dt>
              <dd>{ingresso.venue_name}</dd>
            </div>
            <div className="bilhete-linha">
              <dt>Sala</dt>
              <dd>{ingresso.room_name} · {ingresso.audio}</dd>
            </div>
            <div className="bilhete-linha">
              <dt>Valor</dt>
              <dd>{dinheiro(ingresso.price_cents)}</dd>
            </div>
          </dl>

          {usado && <span className="selo selo--usado">Já utilizado</span>}
          {cancelado && <span className="selo selo--cancelado">Cancelado</span>}

          {/* A explicação fica onde a pessoa procuraria o ingresso, e não
              some junto com ele (D10). */}
          {ingresso.showing_cancelled && (
            <p className="aviso-cancelamento">
              Sessão cancelada pelo cinema
              {ingresso.cancellation_reason && `: ${ingresso.cancellation_reason}`}
              . O valor foi estornado.
            </p>
          )}
        </div>
      </div>

      <div className="bilhete-picote" />

      <div className="bilhete-canhoto">
        {/* O QR fica visível mesmo depois de usado: some-lo esconderia a
            prova de que o ingresso existiu. Apagado, comunica que não vale
            mais sem apagar o registro. */}
        <div className={`bilhete-qr${ativo ? '' : ' bilhete-qr--apagado'}`}>
          <QRCodeSVG value={ingresso.qr_token} size={104} level="M" />
        </div>

        <div className="bilhete-codigo">
          <strong>Código para digitação</strong>
          {ingresso.jti}
        </div>
      </div>

      {ativo && (
        <div className="bilhete-acoes">
          <button
            type="button"
            className="elo"
            onClick={compartilhar}
            disabled={gerando}
          >
            {gerando ? 'Gerando…' : 'Compartilhar'}
          </button>

          <button
            type="button"
            className="elo elo--perigo"
            onClick={() => setConfirmando(true)}
            disabled={cancelando}
          >
            {cancelando ? 'Cancelando…' : 'Cancelar ingresso'}
          </button>
        </div>
      )}

      {confirmando && (
        <Confirmar
          titulo="Cancelar ingresso"
          rotuloConfirmar="Cancelar ingresso"
          aoFechar={() => setConfirmando(false)}
          aoConfirmar={() => { setConfirmando(false); cancelar(); }}
        >
          <p>
            <span className="dialogo-destaque">
              Poltrona {ingresso.seat_label}
            </span>
            {' · '}{ingresso.event_title}
            {' · '}{quando(ingresso.starts_at)}
          </p>
          <p className="dialogo-consequencia">
            A poltrona volta para o mapa e o valor de{' '}
            {dinheiro(ingresso.price_cents)} será estornado. Esta ação é
            irreversível.
          </p>
        </Confirmar>
      )}

      {erro && <p className="aviso-cancelamento">{erro}</p>}

      {link && (
        <div className="compartilhado">
          <p className="compartilhado-url">{link}</p>
          <button type="button" className="elo" onClick={copiar}>
            {copiado ? 'Copiado' : 'Copiar link'}
          </button>
        </div>
      )}
    </article>
  );
}
