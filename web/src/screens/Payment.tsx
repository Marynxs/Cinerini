import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { catalogo, compra } from '../api/endpoints';
import type { OrderOut, PaymentOut, ShowingOut } from '../api/types';
import { Carregando, Layout, Vazio, Voltar } from '../components/Layout';
import { Stepper } from '../components/Stepper';
import './Payment.css';

/* Desfecho determinístico, documentado no README: cartão terminado em zero é
   recusado. Os dois caminhos precisam ser demonstráveis quando se quiser. */
const CARTOES_TESTE = [
  { numero: '4111 1111 1111 1111', efeito: 'Aprovado', recusa: false },
  { numero: '4111 1111 1111 1110', efeito: 'Recusado', recusa: true },
];

const dinheiro = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
  });

const soDigitos = (texto: string) => texto.replace(/\D/g, '');

/** Agrupa de quatro em quatro enquanto digita: 16 dígitos seguidos são
    ilegíveis para conferir contra o cartão físico. */
const formatarCartao = (texto: string) =>
  soDigitos(texto).slice(0, 19).replace(/(.{4})/g, '$1 ').trim();

function Relogio({ ate, aoExpirar }: { ate: string; aoExpirar: () => void }) {
  const [restante, setRestante] = useState(() =>
    Math.max(0, new Date(ate).getTime() - Date.now()));

  useEffect(() => {
    const id = setInterval(() => {
      const falta = Math.max(0, new Date(ate).getTime() - Date.now());
      setRestante(falta);
      if (falta === 0) aoExpirar();
    }, 1000);

    return () => clearInterval(id);
  }, [ate, aoExpirar]);

  const minutos = Math.floor(restante / 60_000);
  const segundos = Math.floor((restante % 60_000) / 1000);
  const acabando = restante < 120_000;

  return (
    <div className={`prazo${acabando ? ' prazo--acabando' : ''}`}>
      <span className="prazo-rotulo">Poltronas reservadas por</span>
      <span className="prazo-valor">
        {minutos}:{String(segundos).padStart(2, '0')}
      </span>
    </div>
  );
}

export function Payment() {
  const { id } = useParams();
  const navegar = useNavigate();
  const orderId = Number(id);

  const [pedido, setPedido] = useState<OrderOut | null>(null);
  const [sessao, setSessao] = useState<ShowingOut | null>(null);
  const [resultado, setResultado] = useState<PaymentOut | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [expirou, setExpirou] = useState(false);

  const [numero, setNumero] = useState('');
  const [titular, setTitular] = useState('');

  useEffect(() => {
    if (Number.isNaN(orderId)) {
      navegar('/', { replace: true });
      return;
    }

    compra.meusPedidos()
      .then(async (pedidos) => {
        const alvo = pedidos.find((p) => p.id === orderId);
        if (!alvo) throw new Error('Pedido não encontrado.');
        setPedido(alvo);
        setSessao(await catalogo.sessao(alvo.showing_id));
      })
      .catch((e: Error) => setErro(e.message));
  }, [navegar, orderId]);

  const poltronas = useMemo(
    () => pedido?.tickets.map((t) => t.seat_label).sort() ?? [],
    [pedido],
  );

  async function pagar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    try {
      const resposta = await compra.pagar(orderId, soDigitos(numero), titular);
      setResultado(resposta);
      // O pedido em memória ficaria com o status anterior, e uma recarga da
      // tela o trataria como não finalizado.
      setPedido(resposta.order);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  if (erro && !pedido) {
    return (
      <Layout>
        <Vazio titulo="Não deu para abrir o pedido">
          <p>{erro}</p>
        </Vazio>
      </Layout>
    );
  }

  if (!pedido || !sessao) {
    return <Layout><Carregando texto="Carregando o pedido" /></Layout>;
  }

  if (resultado) {
    return (
      <Desfecho
        resultado={resultado}
        poltronas={poltronas}
        aoTentarDeNovo={() => { setResultado(null); setNumero(''); }}
        sessaoId={sessao.id}
      />
    );
  }

  // Recusado continua pagável enquanto a reserva não vence — é o caso de
  // quem errou um dígito e vai tentar outro cartão.
  const finalizado = pedido.status === 'paid' || pedido.status === 'cancelled';

  if (expirou || finalizado) {
    return (
      <Layout>
        <Vazio titulo="A reserva expirou">
          <p>
            As poltronas ficaram reservadas por 10 minutos e voltaram para o
            mapa. Escolha de novo — elas podem ainda estar livres.
          </p>
          <p style={{ marginTop: 'var(--e4)' }}>
            <Link to={`/sessoes/${sessao.id}`} className="elo">
              Voltar ao mapa
            </Link>
          </p>
        </Vazio>
      </Layout>
    );
  }

  return (
    <Layout>
      <Voltar para={`/sessoes/${sessao.id}`} texto="Escolher outras poltronas" />
      <Stepper atual="pagamento" />

      <div className="pagamento">
        <section>
          {pedido.held_until && (
            <Relogio ate={pedido.held_until} aoExpirar={() => setExpirou(true)} />
          )}

          <div className="forma">
            <h1 className="forma-titulo">Pagamento</h1>

            {erro && (
              <p className="erro-form" role="alert">
                <span className="erro-form-marca" aria-hidden="true">!</span>
                {erro}
              </p>
            )}

            <form onSubmit={pagar}>
              <label className="campo">
                <span className="campo-rotulo">Número do cartão</span>
                <input
                  className="campo-entrada cartao-numero"
                  value={numero}
                  onChange={(e) => setNumero(formatarCartao(e.target.value))}
                  placeholder="0000 0000 0000 0000"
                  inputMode="numeric"
                  required
                  autoComplete="cc-number"
                />
              </label>

              <label className="campo">
                <span className="campo-rotulo">Nome impresso no cartão</span>
                <input
                  className="campo-entrada"
                  value={titular}
                  onChange={(e) => setTitular(e.target.value)}
                  required
                  minLength={2}
                  autoComplete="cc-name"
                />
              </label>

              <button
                type="submit"
                className="acao"
                disabled={enviando || soDigitos(numero).length < 13}
              >
                {enviando ? 'Processando…' : `Pagar ${dinheiro(pedido.total_cents)}`}
              </button>

              <p className="acao-aviso">
                Cobrança simulada. Nenhuma transação real é feita.
              </p>
            </form>

            <div className="cartoes-teste">
              <p className="contas-titulo">Cartões de teste</p>
              {CARTOES_TESTE.map((cartao) => (
                <button
                  key={cartao.numero}
                  type="button"
                  className="cartao-teste"
                  onClick={() => {
                    setNumero(cartao.numero);
                    setTitular(titular || 'Bruno Tavares');
                  }}
                >
                  <span>{cartao.numero}</span>
                  <span className={`cartao-teste-efeito${
                    cartao.recusa ? ' cartao-teste-efeito--recusa' : ''}`}
                  >
                    {cartao.efeito}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </section>

        <aside className="resumo" aria-label="Resumo do pedido">
          <div className="resumo-cabeca">Seu pedido</div>

          <div className="resumo-corpo">
            <p className="ficha-titulo" style={{ fontSize: '19px' }}>
              {sessao.event_title}
            </p>
            <p className="filme-meta">
              {sessao.venue_name} · {sessao.room_name} · {sessao.audio}
            </p>
            <p className="filme-meta">
              {new Date(sessao.starts_at).toLocaleString('pt-BR', {
                weekday: 'short', day: '2-digit', month: '2-digit',
                hour: '2-digit', minute: '2-digit',
              }).replace(',', '')}
            </p>

            <div style={{ marginTop: 'var(--e4)' }}>
              {poltronas.map((label) => (
                <div className="resumo-linha" key={label}>
                  <span>{label}</span>
                  <span className="resumo-pontos" aria-hidden="true" />
                  <span className="resumo-valor">
                    {dinheiro(sessao.price_cents)}
                  </span>
                </div>
              ))}
            </div>

            <div className="resumo-total">
              <span>Total</span>
              <span className="resumo-total-valor">
                {dinheiro(pedido.total_cents)}
              </span>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}

interface DesfechoProps {
  resultado: PaymentOut;
  poltronas: string[];
  aoTentarDeNovo: () => void;
  sessaoId: number;
}

function Desfecho({
  resultado, poltronas, aoTentarDeNovo, sessaoId,
}: DesfechoProps) {
  const aprovado = resultado.approved;

  return (
    <Layout>
      <Stepper atual="confirmacao" />

      <div className={`desfecho desfecho--${aprovado ? 'aprovado' : 'recusado'}`}>
        <div className="desfecho-marca">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
               aria-hidden="true">
            {aprovado
              ? <path d="M5 12.5l4.5 4.5L19 7.5" />
              : <path d="M6 6l12 12M18 6L6 18" />}
          </svg>
        </div>

        <h1 className="desfecho-titulo">
          {aprovado ? 'Compra confirmada' : 'Pagamento recusado'}
        </h1>

        <p className="desfecho-texto">
          {aprovado
            ? `${poltronas.length === 1 ? 'Sua poltrona' : 'Suas poltronas'} `
              + `${poltronas.join(', ')} — o ingresso com o código já está em `
              + 'Meus ingressos.'
            : `${resultado.reason ?? 'A operadora recusou a cobrança.'} `
              + 'As poltronas continuam reservadas até a espera vencer: '
              + 'dá para tentar outro cartão sem perder a escolha.'}
        </p>

        <div className="desfecho-acoes">
          {aprovado ? (
            <>
              <Link to="/meus-ingressos" className="acao"
                    style={{ textDecoration: 'none', textAlign: 'center' }}>
                Ver meus ingressos
              </Link>
              <Link to="/" className="elo elo--fraco"
                    style={{ alignSelf: 'center' }}>
                Voltar ao catálogo
              </Link>
            </>
          ) : (
            <>
              <button type="button" className="acao" onClick={aoTentarDeNovo}>
                Tentar outro cartão
              </button>
              <Link to={`/sessoes/${sessaoId}`} className="elo elo--fraco"
                    style={{ alignSelf: 'center' }}>
                Escolher poltronas de novo
              </Link>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
