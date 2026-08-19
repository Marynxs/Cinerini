/* Ingresso aberto por link.

   Público: quem tem o link é quem apresenta o ingresso na portaria. Não
   mostra quem comprou, porque o link circula por mensagem e pode chegar a mais
   gente do que o titular pretendia. */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';

import { ApiError } from '../api/client';
import { compartilhamento } from '../api/endpoints';
import type { SharedTicket as Ingresso } from '../api/types';
import { Carregando, Layout, Vazio, Voltar } from '../components/Layout';
import './MyTickets.css';

const quando = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(',', '');

export function SharedTicket() {
  const { token } = useParams();

  const [ingresso, setIngresso] = useState<Ingresso | null>(null);
  const [erro, setErro] = useState<{ titulo: string; texto: string } | null>(null);

  useEffect(() => {
    if (!token) return;

    compartilhamento.abrir(token)
      .then(setIngresso)
      .catch((e: Error) => {
        // 410 e 404 são casos diferentes: um link desativado existiu, um
        // endereço errado nunca existiu. Dizer "não encontrado" nos dois
        // faria quem recebeu achar que digitou errado.
        const desativado = e instanceof ApiError && e.status === 410;
        setErro({
          titulo: desativado ? 'Link desativado' : 'Link não encontrado',
          texto: desativado
            ? 'Quem compartilhou este ingresso desativou o link.'
            : 'Confira o endereço com quem enviou.',
        });
      });
  }, [token]);

  if (erro) {
    return (
      <Layout>
        <Vazio titulo={erro.titulo}>
          <p>{erro.texto}</p>
          <p style={{ marginTop: 'var(--e4)' }}>
            <Link to="/" className="elo">Ver o que está em cartaz</Link>
          </p>
        </Vazio>
      </Layout>
    );
  }

  if (!ingresso) {
    return <Layout><Carregando texto="Abrindo o ingresso" /></Layout>;
  }

  const usado = ingresso.status === 'used';

  return (
    <Layout>
      <Voltar para="/" texto="Ver o que está em cartaz" />

      <div className="ingressos" style={{ maxWidth: '420px', margin: '0 auto' }}>
        <article className={`bilhete${usado ? ' bilhete--usado' : ''}`}>
          <div className="bilhete-corpo">
            {ingresso.poster_url && (
              <img className="bilhete-poster" src={ingresso.poster_url}
                   alt="" loading="eager" />
            )}

            <div>
              <h1 className="bilhete-titulo">{ingresso.event_title}</h1>

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
                <div className="bilhete-endereco">
                  {ingresso.venue_address} · {ingresso.venue_city}
                </div>
                <div className="bilhete-linha">
                  <dt>Sala</dt>
                  <dd>{ingresso.room_name} · {ingresso.audio}</dd>
                </div>
              </dl>

              {usado && <span className="selo selo--usado">Já utilizado</span>}
            </div>
          </div>

          <div className="bilhete-picote" />

          <div className="bilhete-canhoto">
            <div className={`bilhete-qr${usado ? ' bilhete-qr--apagado' : ''}`}>
              <QRCodeSVG value={ingresso.qr_token} size={104} level="M" />
            </div>

            <div className="bilhete-codigo">
              <strong>Apresente na entrada</strong>
              {usado
                ? 'Este ingresso já foi utilizado.'
                : 'A portaria lê o código pela câmera.'}
            </div>
          </div>
        </article>
      </div>
    </Layout>
  );
}
