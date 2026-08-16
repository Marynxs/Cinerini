import { useEffect, useMemo, useState } from 'react';

import { SeatMap, type Seat } from '../components/SeatMap';
import { Stepper } from '../components/Stepper';
import './SeatSelection.css';

/** Mesmo limite do schema da API, para o cliente não descobrir no erro. */
const MAX_POLTRONAS = 10;

export interface Showing {
  id: number;
  starts_at: string;
  audio: string;
  price_cents: number;
  event_title: string;
  poster_url: string | null;
  runtime_minutes: number | null;
  venue_name: string;
  room_name: string;
}

interface Props {
  showing: Showing;
  seats: Seat[];
  onConfirm: (seatIds: number[]) => void;
  submitting?: boolean;
}

const dinheiro = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
  });

const dia = (iso: string) =>
  new Date(iso).toLocaleDateString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit',
  }).replace(',', '');

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit',
  });

const duracao = (minutos: number) =>
  `${Math.floor(minutos / 60)}h${String(minutos % 60).padStart(2, '0')}`;

export function SeatSelection({
  showing, seats, onConfirm, submitting,
}: Props) {
  const [selecionadas, setSelecionadas] = useState<number[]>([]);
  const [limiteAtingido, setLimiteAtingido] = useState(false);

  const escolhidas = useMemo(
    () => seats.filter((a) => selecionadas.includes(a.id))
      .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR', {
        numeric: true,
      })),
    [seats, selecionadas],
  );

  // O aviso some sozinho quando o cliente libera uma poltrona: deixá-lo na
  // tela depois de resolvido viraria ruído.
  useEffect(() => {
    if (selecionadas.length < MAX_POLTRONAS) setLimiteAtingido(false);
  }, [selecionadas.length]);

  const total = escolhidas.length * showing.price_cents;

  function alternar(seatId: number) {
    setSelecionadas((atuais) => {
      if (atuais.includes(seatId)) return atuais.filter((i) => i !== seatId);

      if (atuais.length >= MAX_POLTRONAS) {
        setLimiteAtingido(true);
        return atuais;
      }

      return [...atuais, seatId];
    });
  }

  return (
    <div className="tela">
      <header className="cabecalho">
        <div className="cabecalho-conteudo">
          <span className="marca">Cinerini</span>
        </div>
      </header>

      <main className="corpo">
        <section className="coluna-mapa">
          <div className="ficha">
            {showing.poster_url && (
              <img
                className="ficha-poster"
                src={showing.poster_url}
                alt={`Pôster de ${showing.event_title}`}
                loading="eager"
              />
            )}

            <div>
              <h1 className="ficha-titulo">{showing.event_title}</h1>

              <div className="ficha-dados">
                <div className="dado">
                  <span className="dado-rotulo">Data</span>
                  <span className="dado-valor">{dia(showing.starts_at)}</span>
                </div>
                <div className="dado">
                  <span className="dado-rotulo">Horário</span>
                  <span className="dado-valor">{hora(showing.starts_at)}</span>
                </div>
                <div className="dado">
                  <span className="dado-rotulo">Cinema</span>
                  <span className="dado-valor dado-valor--secundario">
                    {showing.venue_name}
                  </span>
                </div>
                <div className="dado">
                  <span className="dado-rotulo">Sala</span>
                  <span className="dado-valor dado-valor--secundario">
                    {showing.room_name}
                  </span>
                </div>
                <div className="dado">
                  <span className="dado-rotulo">Áudio</span>
                  <span className="dado-valor dado-valor--secundario">
                    {showing.audio}
                  </span>
                </div>
                {showing.runtime_minutes && (
                  <div className="dado">
                    <span className="dado-rotulo">Duração</span>
                    <span className="dado-valor dado-valor--secundario">
                      {duracao(showing.runtime_minutes)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="trilha-area">
            <Stepper atual="poltronas" />
          </div>

          <div className="mapa-area">
            <SeatMap
              seats={seats}
              selected={selecionadas}
              onToggle={alternar}
              disabled={submitting}
            />
          </div>

        </section>

        <div className="coluna-resumo">
        <aside className="resumo" aria-label="Resumo da compra">
          <div className="resumo-cabeca">Sua seleção</div>

          <div className="resumo-corpo">
            <div className="resumo-itens">
              {escolhidas.length === 0 ? (
                <p className="resumo-linha--vazio">
                  Escolha suas poltronas no mapa.
                </p>
              ) : (
                escolhidas.map((assento) => (
                  <div className="resumo-linha" key={assento.id}>
                    <span>
                      {assento.label}
                      {assento.kind === 'accessible' && ' · acessível'}
                    </span>
                    <span className="resumo-pontos" aria-hidden="true" />
                    <span className="resumo-valor">
                      {dinheiro(showing.price_cents)}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="resumo-total">
              <span>Total</span>
              <span className="resumo-total-valor">{dinheiro(total)}</span>
            </div>

            <button
              type="button"
              className="acao"
              disabled={escolhidas.length === 0 || submitting}
              onClick={() => onConfirm(selecionadas)}
            >
              {submitting ? 'Reservando…' : 'Reservar'}
            </button>

            <p className="acao-aviso">
              As poltronas ficam reservadas por 10 minutos.
            </p>
          </div>
        </aside>

        {limiteAtingido && (
          <p className="aviso-limite" role="alert">
            <span className="aviso-limite-marca" aria-hidden="true">!</span>
            Máximo de {MAX_POLTRONAS} poltronas por compra. Libere uma para
            escolher outra.
          </p>
        )}
        </div>
      </main>
    </div>
  );
}
