/* Portaria: valida o ingresso na entrada.

   A tela é usada em pé, com uma fila esperando. Duas consequências mandam no
   desenho: o veredito ocupa a tela inteira, para ser lido de um metro sem
   aproximar o aparelho; e voltar a ler é um gesto só. */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { portaria } from '../api/endpoints';
import type { Gate as Portaria, GateResult, ShowingBrief, Validation } from '../api/types';
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
   preto e branco também — o par carmim/bege é indistinguível para parte das
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
  const [validacao, setValidacao] = useState<Validation | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [digitado, setDigitado] = useState('');
  const [enviando, setEnviando] = useState(false);

  const ehPortaria = user?.role === 'gate';

  useEffect(() => {
    if (!ehPortaria) return;
    portaria.vinculo().then(setVinculo).catch((e: Error) => setErro(e.message));
  }, [ehPortaria]);

  /* Trava contra a segunda leitura do mesmo código.

     A câmera tenta decodificar seis vezes por segundo, e desligá-la depende
     de um novo render. Nesse intervalo o mesmo QR é lido de novo, e a
     segunda resposta viria `already_used` — sobrescrevendo na tela o
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
  const lendo = Boolean(ehPortaria) && validacao === null && !enviando;
  const { video, estado, reiniciar } = useLeitorQr(lendo, validar);

  if (carregando) return <Layout><Carregando /></Layout>;

  if (!ehPortaria) {
    return (
      <Layout>
        <Vazio titulo="Área da portaria">
          <p>Entre com uma conta de portaria para validar ingressos.</p>
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

  return (
    <Layout>
      {/* Qual sessão esta portaria atende, dito antes da primeira leitura:
          sem isso o operador só descobre a que porta atende ao recusar
          alguém. */}
      <div className="portaria-cabeca">
        <div>
          <p className="portaria-etiqueta">Portaria</p>
          <h1 className="portaria-sessao">
            {sessao ? sessao.event_title : 'Sem sessão vinculada'}
          </h1>
        </div>

        {sessao ? (
          <dl className="portaria-ficha">
            <div>
              <dt>Quando</dt>
              <dd>{quando(sessao.starts_at)}</dd>
            </div>
            <div>
              <dt>Onde</dt>
              <dd>{sessao.venue_name} · {sessao.venue_city}</dd>
            </div>
            <div>
              <dt>Sala</dt>
              <dd>{sessao.room_name}</dd>
            </div>
          </dl>
        ) : vinculo && (
          <p className="portaria-solta">
            Peça ao organizador para vincular esta portaria a uma sessão.
          </p>
        )}
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
