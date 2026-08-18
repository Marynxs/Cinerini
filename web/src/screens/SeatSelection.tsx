import { useEffect, useMemo, useRef, useState } from 'react';

import { Link } from 'react-router-dom';

import type { OrderOut, SeatOut, ShowingOut } from '../api/types';
import { SeatMap } from '../components/SeatMap';
import { Stepper } from '../components/Stepper';
import './SeatSelection.css';

/** Mesmo limite do schema da API, para o cliente não descobrir no erro. */
const MAX_POLTRONAS = 10;

interface Props {
  showing: ShowingOut;
  seats: SeatOut[];
  onConfirm: (seatIds: number[]) => void;
  submitting?: boolean;
  /** Mensagem vinda da API, já pronta para exibir. */
  erro?: string | null;
  /** Poltronas que outra pessoa levou durante a escolha. */
  perdidas?: string[];
  /** Reserva do próprio cliente ainda dentro do prazo, se houver. */
  reserva?: OrderOut | null;
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
  showing, seats, onConfirm, submitting, erro, perdidas = [], reserva,
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

  // Reserva aberta chega já marcada no mapa: o cliente voltou para mexer na
  // escolha, e ver as poltronas em branco pareceria tê-las perdido. Depende
  // do id do pedido para não reescrever o que ele desmarcou em seguida.
  useEffect(() => {
    if (reserva) setSelecionadas(reserva.tickets.map((t) => t.seat_id));
  }, [reserva?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  // O aviso some sozinho quando o cliente libera uma poltrona: deixá-lo na
  // tela depois de resolvido viraria ruído.
  useEffect(() => {
    if (selecionadas.length < MAX_POLTRONAS) setLimiteAtingido(false);
  }, [selecionadas.length]);

  // Poltrona perdida sai da seleção sozinha: mantê-la marcada faria o
  // cliente tentar reservar de novo exatamente o que já não está livre.
  useEffect(() => {
    if (perdidas.length === 0) return;
    const idsPerdidos = seats
      .filter((a) => perdidas.includes(a.label))
      .map((a) => a.id);
    if (idsPerdidos.length > 0) {
      setSelecionadas((atuais) => atuais.filter((i) => !idsPerdidos.includes(i)));
    }
  }, [perdidas, seats]);

  const total = escolhidas.length * showing.price_cents;

  /* A barra fixa e o botão do resumo mostram a mesma ação. Observar o botão
     é o que permite apagar a barra exatamente quando o painel completo entra
     em cena, em vez de deixar duas ações iguais visíveis ao mesmo tempo.

     `IntersectionObserver` e não posição de rolagem: a altura do resumo muda
     com o número de poltronas, e comparar coordenadas erraria a cada
     seleção. */
  const acaoRef = useRef<HTMLButtonElement>(null);
  const [resumoVisivel, setResumoVisivel] = useState(false);

  useEffect(() => {
    const alvo = acaoRef.current;
    if (!alvo) return;

    const observador = new IntersectionObserver(
      ([entrada]) => setResumoVisivel(entrada.isIntersecting),
      // A barra tem cerca de 76px: sem descontá-los, ela só sumiria depois
      // de já estar cobrindo o botão que a substitui.
      { rootMargin: '0px 0px -76px 0px' },
    );

    observador.observe(alvo);
    return () => observador.disconnect();
  }, []);

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
          <Link to="/" className="marca">Cinerini</Link>
          <Link to="/" className="voltar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                 aria-hidden="true">
              <path d="M15 5l-7 7 7 7" />
            </svg>
            Voltar ao catálogo
          </Link>
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

          {reserva && (
            <p className="reserva-aberta">
              <span>
                Você tem uma reserva em andamento nesta sessão. Altere as
                poltronas abaixo ou siga para o pagamento.
              </span>
              <Link to={`/pedidos/${reserva.id}/pagamento`} className="elo">
                Pagar agora
              </Link>
            </p>
          )}

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
              ref={acaoRef}
              type="button"
              className="acao"
              disabled={escolhidas.length === 0 || submitting}
              onClick={() => onConfirm(selecionadas)}
            >
              {submitting ? 'Reservando…'
                : reserva ? 'Atualizar reserva' : 'Reservar'}
            </button>

            <p className="acao-aviso">
              {reserva
                ? 'A reserva anterior é substituída por esta.'
                : 'As poltronas ficam reservadas por 10 minutos.'}
            </p>
          </div>
        </aside>

        {erro && (
          <p className="aviso-limite" role="alert">
            <span className="aviso-limite-marca" aria-hidden="true">!</span>
            {erro}
          </p>
        )}

        {limiteAtingido && (
          <p className="aviso-limite" role="alert">
            <span className="aviso-limite-marca" aria-hidden="true">!</span>
            Máximo de {MAX_POLTRONAS} poltronas por compra. Libere uma para
            escolher outra.
          </p>
        )}
        </div>
      </main>

      {/* Barra fixa do celular: total e ação sempre à mão, sem obrigar a
          rolar até o fim para saber quanto deu.

          Ela se apaga quando o botão do resumo aparece na tela — em vez de
          duas ações iguais empilhadas, o painel completo "absorve" a barra
          ao ser alcançado. */}
      <div
        className={`barra-fixa${resumoVisivel ? ' barra-fixa--oculta' : ''}`}
        aria-hidden={resumoVisivel}
      >
        <div className="barra-fixa-info">
          <span className="barra-fixa-conta">
            {escolhidas.length === 0
              ? 'Nenhuma poltrona'
              : `${escolhidas.length} ${
                  escolhidas.length === 1 ? 'poltrona' : 'poltronas'}`}
          </span>
          <span className="barra-fixa-total">{dinheiro(total)}</span>
        </div>

        <button
          type="button"
          className="acao barra-fixa-acao"
          disabled={escolhidas.length === 0 || submitting || resumoVisivel}
          onClick={() => onConfirm(selecionadas)}
        >
          {submitting ? 'Reservando…'
            : reserva ? 'Atualizar' : 'Reservar'}
        </button>
      </div>
    </div>
  );
}
