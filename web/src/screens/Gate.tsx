/* Portaria: valida o ingresso na entrada.

   A tela é usada em pé, com uma fila esperando. Duas consequências mandam no
   desenho: o veredito ocupa a tela inteira, para ser lido de um metro sem
   aproximar o aparelho; e voltar a ler é um gesto só. */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { portaria } from '../api/endpoints';
import type {
  Gate as Portaria, GateResult, ShowingBrief, Validation,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Carregando, Layout, Vazio } from '../components/Layout';
import { useLeitorQr } from './useLeitorQr';
import './Gate.css';

const quando = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(',', '');

/* Cada veredito tem palavra, explicação e uma marca própria. O par
   fundo/borda vive no CSS, e a distinção não depende de cor: cheio escuro,
   cheio carmim, contorno espesso, tracejado, duplo e hachurado se separam no
   preto e branco também, porque o par carmim/bege é indistinguível para parte das
   pessoas. */
const VEREDITOS: Record<GateResult, { palavra: string; explica: string }> = {
  valid: { palavra: 'Válido', explica: 'Pode entrar.' },
  already_used: {
    palavra: 'Já utilizado',
    explica: 'Este ingresso já passou pela entrada.',
  },
  wrong_showing: {
    palavra: 'Outra sessão',
    explica: 'Filme certo, sessão errada. Encaminhe para a sessão abaixo.',
  },
  wrong_event: {
    palavra: 'Outro evento',
    explica: 'O ingresso é legítimo, mas é de outro filme.',
  },
  cancelled: {
    palavra: 'Cancelado',
    explica: 'Este ingresso foi cancelado e o valor, estornado.',
  },
  invalid: {
    palavra: 'Inválido',
    explica: 'O código não confere com nenhum ingresso emitido.',
  },
};

function Marca({ resultado }: { resultado: GateResult }) {
  const comum = {
    viewBox: '0 0 48 48', fill: 'none', stroke: 'currentColor',
    strokeWidth: 3.5, strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const, 'aria-hidden': true,
    className: 'veredito-marca',
  };

  switch (resultado) {
    case 'valid':
      return <svg {...comum}><path d="M10 25l10 10 18-22" /></svg>;

    case 'invalid':
      return <svg {...comum}><path d="M13 13l22 22M35 13L13 35" /></svg>;

    case 'already_used':
      // Relógio parado: o que distingue este caso é o tempo já gasto.
      return (
        <svg {...comum}>
          <circle cx="24" cy="24" r="16" />
          <path d="M24 14v10l7 5" />
        </svg>
      );

    case 'wrong_showing':
      // Seta circular: mesmo lugar, outro horário.
      return (
        <svg {...comum}>
          <path d="M38 24a14 14 0 1 1-4.5-10.3" />
          <path d="M38 8v7h-7" />
          <path d="M24 16v8l5 4" />
        </svg>
      );

    case 'wrong_event':
      // Seta reta: não é barrado, é mandado para outro lugar.
      return <svg {...comum}><path d="M8 24h30M26 12l12 12-12 12" /></svg>;

    default:
      return (
        <svg {...comum}>
          <circle cx="24" cy="24" r="16" />
          <path d="M13 13l22 22" />
        </svg>
      );
  }
}

/** A sessão a que o ingresso pertence, em ficha de conferência. */
function Sessao({ sessao }: { sessao: ShowingBrief }) {
  return (
    <>
      <div>
        <dt>Sessão</dt>
        <dd>{sessao.event_title}</dd>
      </div>
      <div>
        <dt>Quando</dt>
        <dd>{quando(sessao.starts_at)}</dd>
      </div>
      <div>
        <dt>Onde</dt>
        <dd>{sessao.venue_name} · {sessao.room_name}</dd>
      </div>
    </>
  );
}

function Veredito(
  { validacao, aoSeguir }: { validacao: Validation; aoSeguir: () => void },
) {
  const { palavra, explica } = VEREDITOS[validacao.result];

  // Foco no botão assim que o veredito aparece: quem opera repete o gesto
  // dezenas de vezes e não deveria procurar onde clicar a cada ingresso.
  const focar = useCallback((n: HTMLButtonElement | null) => n?.focus(), []);

  return (
    <div className={`veredito veredito--${validacao.result}`} role="alert">
      <Marca resultado={validacao.result} />

      <p className="veredito-palavra">{palavra}</p>
      <p className="veredito-explica">{explica}</p>

      {(validacao.seat_label || validacao.showing) && (
        <dl className="veredito-ficha">
          {validacao.seat_label && (
            <div>
              <dt>Poltrona</dt>
              <dd className="veredito-poltrona">{validacao.seat_label}</dd>
            </div>
          )}
          {validacao.customer_name && (
            <div>
              <dt>Cliente</dt>
              <dd>{validacao.customer_name}</dd>
            </div>
          )}
          {validacao.showing && <Sessao sessao={validacao.showing} />}
          {validacao.used_at && (
            <div>
              <dt>Entrou em</dt>
              <dd>{quando(validacao.used_at)}</dd>
            </div>
          )}
        </dl>
      )}

      <button type="button" className="veredito-seguir" onClick={aoSeguir}
              ref={focar}>
        Ler o próximo
      </button>
    </div>
  );
}

export function Gate() {
  const { user, carregando } = useAuth();

  const [vinculo, setVinculo] = useState<Portaria | null>(null);
  const [turnos, setTurnos] = useState<ShowingBrief[] | null>(null);
  const [validacao, setValidacao] = useState<Validation | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [digitado, setDigitado] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [trocando, setTrocando] = useState(false);

  /* Quem valida, e não quem "é" a portaria: o organizador abre a mesma tela
     pelo próprio papel (D27). A API já concordava, e era só o front que
     escondia o caminho. */
  const podeValidar = user?.role === 'gate' || user?.role === 'organizer';

  useEffect(() => {
    if (!podeValidar) return;
    portaria.vinculo().then(setVinculo).catch((e: Error) => setErro(e.message));
  }, [podeValidar]);

  // Os turnos só são buscados quando há o que escolher: com a sessão já
  // definida, a tela vai direto para a câmera.
  const precisaEscolher = podeValidar && (vinculo?.showing_id == null || trocando);

  useEffect(() => {
    if (!precisaEscolher) return;
    setTurnos(null);
    portaria.turnos().then(setTurnos).catch((e: Error) => setErro(e.message));
  }, [precisaEscolher]);

  async function escolher(showingId: number | null) {
    setErro(null);
    try {
      setVinculo(await portaria.escolherTurno(showingId));
      setTrocando(false);
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  /* Trava contra a segunda leitura do mesmo código.

     A câmera tenta decodificar seis vezes por segundo, e desligá-la depende
     de um novo render. Nesse intervalo o mesmo QR é lido de novo, e a
     segunda resposta viria `already_used`, sobrescrevendo na tela o
     `valid` da primeira e mandando embora quem tinha ingresso bom.

     Precisa ser `ref` e não estado: estado só vale no próximo render, e a
     corrida acontece justamente antes dele. */
  const emVoo = useRef(false);

  const validar = useCallback(async (codigo: string) => {
    const limpo = codigo.trim();
    if (!limpo || emVoo.current) return;

    emVoo.current = true;
    setEnviando(true);
    setErro(null);
    try {
      setValidacao(await portaria.validar(limpo));
      setDigitado('');
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      emVoo.current = false;
      setEnviando(false);
    }
  }, []);

  // A câmera desliga enquanto há veredito na tela e enquanto uma validação
  // está no ar. Sem isso, o mesmo QR seria lido seis vezes por segundo.
  const lendo = Boolean(podeValidar) && !precisaEscolher
    && validacao === null && !enviando;
  const { video, estado, reiniciar } = useLeitorQr(lendo, validar);

  if (carregando) return <Layout><Carregando /></Layout>;

  if (!podeValidar) {
    return (
      <Layout>
        <Vazio titulo="Área da portaria">
          <p>
            Entre com uma conta de funcionário ou de organizador para validar
            ingressos.
          </p>
          <p style={{ marginTop: 'var(--e4)' }}>
            <Link to="/entrar" state={{ de: '/portaria' }} className="elo">
              Entrar
            </Link>
          </p>
        </Vazio>
      </Layout>
    );
  }

  if (validacao) {
    return (
      <Layout semPadding>
        <Veredito validacao={validacao} aoSeguir={() => setValidacao(null)} />
      </Layout>
    );
  }

  const sessao = vinculo?.showing;

  /* Escolher o turno é o primeiro gesto de quem chega para trabalhar. Fica
     antes da câmera porque validar sem saber que sessão se atende é como a
     porta aceitar qualquer um, e porque o operador troca de sessão sozinho
     ao longo da noite, sem depender do organizador (D24). */
  if (precisaEscolher) {
    return (
      <Layout>
        <div className="portaria-cabeca">
          <div>
            <p className="portaria-etiqueta">Funcionário · {vinculo?.name}</p>
            <h1 className="portaria-sessao">
              {trocando ? 'Trocar de sessão' : 'Qual sessão você atende?'}
            </h1>
          </div>
          {vinculo?.venue_name && (
            <p className="portaria-cinema">{vinculo.venue_name}</p>
          )}
        </div>

        {erro && (
          <p className="erro-form" role="alert" style={{ marginTop: 'var(--e4)' }}>
            <span className="erro-form-marca" aria-hidden="true">!</span>{erro}
          </p>
        )}

        {turnos === null && !erro && <Carregando texto="Buscando sessões" />}

        {turnos?.length === 0 && (
          <Vazio titulo="Nenhuma sessão por perto">
            <p>
              Não há sessões deste cinema começando nas próximas horas. Assim
              que houver, elas aparecem aqui.
            </p>
          </Vazio>
        )}

        {turnos && turnos.length > 0 && (
          <ul className="turnos">
            {turnos.map((s) => {
              // A sessão atual fica marcada com borda cheia: sem isso, quem
              // abriu a lista para trocar não sabe de onde está saindo.
              const atual = s.showing_id === vinculo?.showing_id;

              return (
                <li key={s.showing_id}>
                  <button
                    type="button"
                    className={`turno${atual ? ' turno--atual' : ''}`}
                    aria-current={atual ? 'true' : undefined}
                    onClick={() => escolher(atual ? null : s.showing_id)}
                  >
                    <span className="turno-hora">{quando(s.starts_at)}</span>
                    <span className="turno-filme">{s.event_title}</span>
                    <span className="turno-sala">
                      {atual ? 'Atendendo · toque para sair' : s.room_name}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {/* Ficar sem turno é estado legítimo, não falha de cadastro: entre
            uma sessão e a seguinte a porta não deve aceitar nada. Precisa
            de caminho próprio, senão só se sai de um turno entrando em
            outro. */}
        {turnos && turnos.length > 0 && vinculo?.showing_id != null && (
          <p className="turnos-sair">
            <button type="button" className="elo elo--perigo"
                    onClick={() => escolher(null)}>
              Encerrar turno e não validar nada
            </button>
          </p>
        )}

        {trocando && (
          <p style={{ marginTop: 'var(--e5)' }}>
            <button type="button" className="elo elo--fraco"
                    onClick={() => setTrocando(false)}>
              Continuar na sessão atual
            </button>
          </p>
        )}
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Qual sessão esta portaria atende, dito antes da primeira leitura:
          sem isso o operador só descobre a que porta atende ao recusar
          alguém. */}
      <div className="portaria-cabeca">
        <div>
          <p className="portaria-etiqueta">Portaria · {vinculo?.name}</p>
          <h1 className="portaria-sessao">{sessao?.event_title}</h1>
        </div>

        <div>
          <dl className="portaria-ficha">
            <div>
              <dt>Quando</dt>
              <dd>{sessao && quando(sessao.starts_at)}</dd>
            </div>
            <div>
              <dt>Onde</dt>
              <dd>{sessao?.venue_name} · {sessao?.venue_city}</dd>
            </div>
            <div>
              <dt>Sala</dt>
              <dd>{sessao?.room_name}</dd>
            </div>
          </dl>

          <button type="button" className="elo elo--fraco portaria-trocar"
                  onClick={() => setTrocando(true)}>
            Trocar de sessão
          </button>
        </div>
      </div>

      <div className="camera">
        <video ref={video} className="camera-video" playsInline muted
               autoPlay aria-label="Imagem da câmera" />
        <div className="camera-mira" aria-hidden="true" />

        {estado !== 'lendo' && (
          <div className="camera-aviso">
            {estado === 'iniciando' && <p>Ligando a câmera…</p>}
            {estado === 'negada' && (
              <p>
                Permissão de câmera negada. Autorize nas configurações do
                navegador, ou digite o código abaixo.
              </p>
            )}
            {estado === 'ausente' && (
              <p>Nenhuma câmera disponível. Use a digitação abaixo.</p>
            )}
            {estado === 'falhou' && (
              <p>A câmera não abriu. Use a digitação abaixo.</p>
            )}
            {(estado === 'negada' || estado === 'falhou') && (
              <button type="button" className="botao-compacto botao-compacto--vazado"
                      onClick={reiniciar}>
                Tentar de novo
              </button>
            )}
          </div>
        )}
      </div>

      <form
        className="digitacao"
        onSubmit={(e) => { e.preventDefault(); validar(digitado); }}
      >
        <label className="campo">
          <span className="campo-rotulo">Ou digite o código do ingresso</span>
          <input
            className="campo-entrada"
            value={digitado}
            onChange={(e) => setDigitado(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
          />
        </label>

        <button type="submit" className="acao" disabled={enviando || !digitado.trim()}>
          {enviando ? 'Validando…' : 'Validar'}
        </button>
      </form>

      {erro && (
        <p className="erro-form" role="alert">
          <span className="erro-form-marca" aria-hidden="true">!</span>
          {erro}
        </p>
      )}
    </Layout>
  );
}
