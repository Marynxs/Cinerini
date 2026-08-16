/* Liga a tela de escolha de poltrona à API.

   A tela em si não sabe de rede: recebe dados e devolve a seleção. Assim ela
   continua verificável isoladamente, e toda falha de rede é tratada aqui. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ApiError } from '../api/client';
import { catalogo, compra } from '../api/endpoints';
import type { OrderOut, SeatOut, ShowingOut } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Carregando, Layout, Vazio } from '../components/Layout';
import { SeatSelection } from './SeatSelection';

export function SeatSelectionPage() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { user, carregando: carregandoSessao } = useAuth();

  const showingId = Number(id);

  const [sessao, setSessao] = useState<ShowingOut | null>(null);
  const [assentos, setAssentos] = useState<SeatOut[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [perdidas, setPerdidas] = useState<string[]>([]);
  const [reserva, setReserva] = useState<OrderOut | null>(null);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      const [s, a] = await Promise.all([
        catalogo.sessao(showingId),
        catalogo.assentos(showingId),
      ]);
      setSessao(s);
      setAssentos(a);
    } catch (e) {
      setErro((e as Error).message);
    }
  }, [showingId]);

  // Reserva aberta desta sessão, se houver. Sem isso as poltronas do próprio
  // cliente apareceriam como ocupadas por terceiros, e não haveria caminho
  // de volta ao pagamento.
  const buscarReserva = useCallback(async () => {
    if (!user) {
      setReserva(null);
      return;
    }

    try {
      const pedidos = await compra.meusPedidos();
      const aberta = pedidos.find((p) =>
        p.showing_id === showingId
        && (p.status === 'pending' || p.status === 'refused')
        && p.held_until !== null
        && new Date(p.held_until).getTime() > Date.now());

      setReserva(aberta ?? null);
    } catch {
      // Falhar aqui não pode impedir a escolha de poltronas: é informação
      // auxiliar, não parte do fluxo principal.
      setReserva(null);
    }
  }, [showingId, user]);

  useEffect(() => {
    if (Number.isNaN(showingId)) {
      navegar('/', { replace: true });
      return;
    }
    carregar();
    buscarReserva();
  }, [buscarReserva, carregar, navegar, showingId]);

  async function reservar(seatIds: number[]) {
    // Quem não entrou vai para o login e volta para cá — perder a seleção
    // seria punir a pessoa por não ter previsto que precisaria de conta.
    if (!user) {
      navegar('/entrar', { state: { de: `/sessoes/${showingId}` } });
      return;
    }

    setEnviando(true);
    setErro(null);
    setPerdidas([]);

    try {
      const pedido = await compra.reservar(showingId, seatIds);
      navegar(`/pedidos/${pedido.id}/pagamento`);
    } catch (e) {
      if (e instanceof ApiError && e.seats.length > 0) {
        // Alguém levou a poltrona no meio do caminho. Recarregar o mapa é
        // obrigatório: continuar mostrando a poltrona livre repetiria o erro.
        setPerdidas(e.seats);
        await carregar();
      }
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  if (erro && !sessao) {
    return (
      <Layout>
        <Vazio titulo="Não deu para abrir a sessão">
          <p>{erro}</p>
        </Vazio>
      </Layout>
    );
  }

  // As poltronas da própria reserva não são obstáculo para quem as reservou:
  // o mapa as trata como livres, e a tela as devolve já selecionadas para o
  // cliente poder trocar ou desmarcar.
  const meusIds = new Set(reserva?.tickets.map((t) => t.seat_id) ?? []);
  const mapa = assentos?.map((a) =>
    (meusIds.has(a.id) ? { ...a, taken: false } : a));

  if (!sessao || !mapa || carregandoSessao) {
    return (
      <Layout>
        <Carregando texto="Carregando o mapa" />
      </Layout>
    );
  }

  return (
    <SeatSelection
      showing={sessao}
      seats={mapa}
      onConfirm={reservar}
      submitting={enviando}
      erro={erro}
      perdidas={perdidas}
      reserva={reserva}
    />
  );
}
