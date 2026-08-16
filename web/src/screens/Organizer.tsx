/* Painel do organizador: cinemas, salas, eventos e sessões numa tela só.

   Uma tela em vez de várias porque as quatro coisas se encadeiam — não dá
   para criar sessão sem sala, nem publicar evento sem sessão — e navegar
   entre abas para completar um cadastro esconderia essa dependência. */

import { useCallback, useEffect, useState, type FormEvent } from 'react';

import { catalogo, organizador } from '../api/endpoints';
import type {
  EventOut, Room, ShowingOut, TmdbSearchResult, Venue,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Confirmar } from '../components/Confirmar';
import { Carregando, Layout, Vazio } from '../components/Layout';
import './Organizer.css';

const dinheiro = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
  });

const quando = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  }).replace(',', '');

/** Junta data e hora locais num instante absoluto.

    Dois campos em vez de um `datetime-local`: o campo combinado esconde a
    parte da hora quando o layout o aperta, e o organizador ficava sem como
    informar o horário. Separados, cada um tem largura própria e rótulo. */
const paraISO = (data: string, hora: string) =>
  new Date(`${data}T${hora}`).toISOString();

export function Organizer() {
  const { user, carregando } = useAuth();

  const [venues, setVenues] = useState<Venue[]>([]);
  const [salas, setSalas] = useState<Record<number, Room[]>>({});
  const [eventos, setEventos] = useState<EventOut[] | null>(null);
  const [sessoes, setSessoes] = useState<Record<number, ShowingOut[]>>({});
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    setErro(null);
    try {
      const [cinemas, meus] = await Promise.all([
        catalogo.cinemas(),
        organizador.meusEventos(),
      ]);
      setVenues(cinemas);
      setEventos(meus);

      const porCinema = await Promise.all(
        cinemas.map(async (v) => [v.id, await catalogo.salas(v.id)] as const));
      setSalas(Object.fromEntries(porCinema));

      const porEvento = await Promise.all(
        meus.map(async (e) => [e.id, await catalogo.sessoes(e.id)] as const));
      setSessoes(Object.fromEntries(porEvento));
    } catch (e) {
      setErro((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (!carregando && user?.role === 'organizer') recarregar();
  }, [carregando, recarregar, user]);

  if (carregando) return <Layout><Carregando /></Layout>;

  if (user?.role !== 'organizer') {
    return (
      <Layout>
        <Vazio titulo="Área do organizador">
          <p>Entre com uma conta de organizador para gerenciar eventos.</p>
        </Vazio>
      </Layout>
    );
  }

  const todasSalas = Object.values(salas).flat();

  return (
    <Layout>
      <div className="catalogo-cabeca">
        <h1 className="catalogo-titulo">Painel</h1>
        <span className="catalogo-contagem">
          {eventos?.length ?? 0} eventos · {venues.length} cinemas
        </span>
      </div>

      {erro && (
        <p className="erro-form" role="alert" style={{ marginTop: 'var(--e4)' }}>
          <span className="erro-form-marca" aria-hidden="true">!</span>{erro}
        </p>
      )}

      <NovoEvento aoCriar={recarregar} />

      <section className="painel-secao">
        <h2 className="painel-titulo">Meus eventos</h2>

        {eventos === null && <Carregando />}

        {eventos?.length === 0 && (
          <p className="vazio-linha">
            Nenhum evento ainda. Busque um filme acima para criar o primeiro.
          </p>
        )}

        {eventos?.map((evento) => (
          <Evento
            key={evento.id}
            evento={evento}
            sessoes={sessoes[evento.id] ?? []}
            salas={todasSalas}
            venues={venues}
            aoMudar={recarregar}
          />
        ))}
      </section>

      <Cinemas venues={venues} salas={salas} aoMudar={recarregar} />
    </Layout>
  );
}

/* ------------------------------------------------------ novo evento */

function NovoEvento({ aoCriar }: { aoCriar: () => void }) {
  const [termo, setTermo] = useState('');
  const [achados, setAchados] = useState<TmdbSearchResult[] | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function buscar(evento: FormEvent) {
    evento.preventDefault();
    setBuscando(true);
    setErro(null);
    try {
      setAchados(await organizador.buscarFilme(termo));
    } catch (e) {
      setErro((e as Error).message);
      setAchados(null);
    } finally {
      setBuscando(false);
    }
  }

  async function criar(filme: TmdbSearchResult) {
    try {
      await organizador.criarEvento(filme.tmdb_id);
      setAchados(null);
      setTermo('');
      aoCriar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <section className="painel-secao">
      <h2 className="painel-titulo">Novo evento a partir do catálogo</h2>

      <form className="forma-inline" onSubmit={buscar} style={{ border: 'none', padding: 0 }}>
        <div className="campo-curto" style={{ flex: '1 1 260px' }}>
          <span className="campo-rotulo">Título do filme</span>
          <input
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Duna, Matrix, Cidade de Deus…"
            minLength={2}
            required
          />
        </div>
        <button type="submit" className="botao-compacto" disabled={buscando}>
          {buscando ? 'Buscando…' : 'Buscar no TMDb'}
        </button>
      </form>

      {erro && <p className="motivo" style={{ marginTop: 'var(--e2)' }}>{erro}</p>}

      {achados?.length === 0 && (
        <p className="vazio-linha">Nenhum filme encontrado para "{termo}".</p>
      )}

      {achados && achados.length > 0 && (
        <div className="tmdb-lista">
          {achados.slice(0, 12).map((filme) => (
            <button
              key={filme.tmdb_id}
              type="button"
              className="tmdb-item"
              onClick={() => criar(filme)}
            >
              {filme.poster_url
                ? <img className="tmdb-poster" src={filme.poster_url} alt="" />
                : <span className="tmdb-poster" />}
              <span>
                <span className="tmdb-titulo">{filme.title}</span>
                <span className="tmdb-ano">
                  {filme.year ?? 'sem data'} · criar evento
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

/* ---------------------------------------------------------- evento */

interface EventoProps {
  evento: EventOut;
  sessoes: ShowingOut[];
  salas: Room[];
  venues: Venue[];
  aoMudar: () => void;
}

function Evento({ evento, sessoes, salas, venues, aoMudar }: EventoProps) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aCancelar, setACancelar] = useState<ShowingOut | null>(null);

  async function agir(acao: () => Promise<unknown>) {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  const publicado = evento.status === 'published';

  return (
    <article className="evento">
      <div className="evento-cabeca">
        <span className="evento-nome">{evento.title}</span>

        <div className="evento-acoes">
          <span className={`marca-estado marca-estado--${
            publicado ? 'publicado' : 'rascunho'}`}
          >
            {publicado ? 'Publicado' : 'Rascunho'}
          </span>

          <button
            type="button"
            className="botao-compacto botao-compacto--vazado"
            disabled={ocupado || (!publicado && sessoes.length === 0)}
            title={!publicado && sessoes.length === 0
              ? 'Cadastre uma sessão antes de publicar' : undefined}
            onClick={() => agir(() => publicado
              ? organizador.despublicar(evento.id)
              : organizador.publicar(evento.id))}
          >
            {publicado ? 'Despublicar' : 'Publicar'}
          </button>
        </div>
      </div>

      {erro && <p className="motivo" style={{ padding: '0 var(--e4)' }}>{erro}</p>}

      {sessoes.length === 0 ? (
        <p className="vazio-linha">Nenhuma sessão cadastrada.</p>
      ) : (
        <table className="tabela">
          <thead>
            <tr>
              <th>Quando</th>
              <th>Cinema</th>
              <th>Sala</th>
              <th>Áudio</th>
              <th className="tabela-num">Preço</th>
              <th className="tabela-num">Ocupação</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {sessoes.map((s) => {
              const cancelada = Boolean(s.cancelled_at);
              const vendidos = s.seats_total - s.seats_available;

              return (
                <tr key={s.id} className={cancelada ? 'linha-cancelada' : ''}>
                  <td>{quando(s.starts_at)}</td>
                  <td>{s.venue_name}</td>
                  <td>{s.room_name}</td>
                  <td>{s.audio}</td>
                  <td className="tabela-num">{dinheiro(s.price_cents)}</td>
                  <td className="tabela-num">
                    {cancelada
                      ? <span className="motivo">{s.cancellation_reason}</span>
                      : `${vendidos}/${s.seats_total}`}
                  </td>
                  <td className="tabela-num">
                    {!cancelada && (
                      <button
                        type="button"
                        className="botao-compacto botao-compacto--perigo"
                        disabled={ocupado}
                        onClick={() => setACancelar(s)}
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <NovaSessao
        eventoId={evento.id}
        salas={salas}
        venues={venues}
        aoCriar={aoMudar}
      />

      {aCancelar && (
        <Confirmar
          titulo="Cancelar sessão"
          rotuloConfirmar="Cancelar sessão"
          motivo={{ rotulo: 'Motivo', sugestao: 'Problema no projetor' }}
          aoFechar={() => setACancelar(null)}
          aoConfirmar={(motivo) => {
            const sessao = aCancelar;
            setACancelar(null);
            agir(() => organizador.cancelarSessao(sessao.id, motivo));
          }}
        >
          <p>
            <span className="dialogo-destaque">{evento.title}</span>
            {' · '}{quando(aCancelar.starts_at)}
            {' · '}{aCancelar.venue_name}, {aCancelar.room_name}
          </p>
          <p className="dialogo-consequencia">
            {aCancelar.seats_total - aCancelar.seats_available === 0
              ? 'Nenhum ingresso vendido até agora.'
              : `${aCancelar.seats_total - aCancelar.seats_available} `
                + 'ingresso(s) serão cancelados e estornados.'}
            {' '}O motivo abaixo aparece para quem comprou. Esta ação é
            irreversível.
          </p>
        </Confirmar>
      )}
    </article>
  );
}

/* --------------------------------------------------------- sessão */

interface NovaSessaoProps {
  eventoId: number;
  salas: Room[];
  venues: Venue[];
  aoCriar: () => void;
}

function NovaSessao({ eventoId, salas, venues, aoCriar }: NovaSessaoProps) {
  const [roomId, setRoomId] = useState('');
  const [data, setData] = useState('');
  const [hora, setHora] = useState('19:00');
  const [preco, setPreco] = useState('32,00');
  const [audio, setAudio] = useState('Dublado');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function criar(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);

    try {
      // Centavos como inteiro do começo ao fim: converter só na fronteira
      // evita que o float apareça em qualquer lugar.
      const centavos = Math.round(
        Number(preco.replace(/\./g, '').replace(',', '.')) * 100);

      await organizador.criarSessao(eventoId, {
        room_id: Number(roomId),
        starts_at: paraISO(data, hora),
        price_cents: centavos,
        audio,
      });

      setData('');
      aoCriar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  if (salas.length === 0) {
    return (
      <p className="vazio-linha">
        Cadastre um cinema e uma sala abaixo para poder criar sessões.
      </p>
    );
  }

  return (
    <form className="forma-inline" onSubmit={criar}>
      <div className="campo-curto">
        <span className="campo-rotulo">Sala</span>
        <select value={roomId} onChange={(e) => setRoomId(e.target.value)} required>
          <option value="">Escolha</option>
          {salas.map((sala) => (
            <option key={sala.id} value={sala.id}>
              {venues.find((v) => v.id === sala.venue_id)?.name} — {sala.name}
            </option>
          ))}
        </select>
      </div>

      <div className="campo-curto">
        <span className="campo-rotulo">Data</span>
        <input
          type="date"
          value={data}
          onChange={(e) => setData(e.target.value)}
          className="campo-data"
          required
        />
      </div>

      <div className="campo-curto">
        <span className="campo-rotulo">Horário</span>
        <input
          type="time"
          value={hora}
          onChange={(e) => setHora(e.target.value)}
          className="campo-hora"
          required
        />
      </div>

      <div className="campo-curto">
        <span className="campo-rotulo">Preço</span>
        <input
          value={preco}
          onChange={(e) => setPreco(e.target.value)}
          style={{ width: '80px' }}
          required
        />
      </div>

      <div className="campo-curto">
        <span className="campo-rotulo">Áudio</span>
        <select value={audio} onChange={(e) => setAudio(e.target.value)}>
          <option>Dublado</option>
          <option>Legendado</option>
        </select>
      </div>

      <button type="submit" className="botao-compacto" disabled={enviando}>
        {enviando ? 'Criando…' : 'Adicionar sessão'}
      </button>

      {erro && <span className="motivo">{erro}</span>}
    </form>
  );
}

/* -------------------------------------------------- cinemas e salas */

interface CinemasProps {
  venues: Venue[];
  salas: Record<number, Room[]>;
  aoMudar: () => void;
}

function Cinemas({ venues, salas, aoMudar }: CinemasProps) {
  const [erro, setErro] = useState<string | null>(null);

  const [nome, setNome] = useState('');
  const [cidade, setCidade] = useState('');
  const [uf, setUf] = useState('');
  const [endereco, setEndereco] = useState('');

  async function criarCinema(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await organizador.criarCinema({
        name: nome, city: cidade, state: uf, address: endereco,
      });
      setNome(''); setCidade(''); setUf(''); setEndereco('');
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <section className="painel-secao">
      <h2 className="painel-titulo">Cinemas e salas</h2>

      {erro && <p className="motivo">{erro}</p>}

      {venues.map((venue) => (
        <article className="evento" key={venue.id}>
          <div className="evento-cabeca">
            <span className="evento-nome">{venue.name}</span>
            <span className="cinema-cidade">{venue.city} · {venue.state}</span>
          </div>

          {(salas[venue.id]?.length ?? 0) === 0 ? (
            <p className="vazio-linha">Nenhuma sala cadastrada.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Sala</th>
                  <th className="tabela-num">Fileiras</th>
                  <th className="tabela-num">Por fileira</th>
                  <th className="tabela-num">Capacidade</th>
                </tr>
              </thead>
              <tbody>
                {salas[venue.id].map((sala) => (
                  <tr key={sala.id}>
                    <td>{sala.name}</td>
                    <td className="tabela-num">{sala.rows}</td>
                    <td className="tabela-num">{sala.seats_per_row}</td>
                    <td className="tabela-num">{sala.capacity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <NovaSala venueId={venue.id} aoCriar={aoMudar} />
        </article>
      ))}

      <form className="forma-inline" onSubmit={criarCinema}
            style={{ border: 'none', paddingLeft: 0 }}>
        <div className="campo-curto">
          <span className="campo-rotulo">Novo cinema</span>
          <input value={nome} onChange={(e) => setNome(e.target.value)}
                 placeholder="Nome" minLength={2} required />
        </div>
        <div className="campo-curto">
          <span className="campo-rotulo">Cidade</span>
          <input value={cidade} onChange={(e) => setCidade(e.target.value)}
                 minLength={2} required />
        </div>
        <div className="campo-curto">
          <span className="campo-rotulo">UF</span>
          <input value={uf} onChange={(e) => setUf(e.target.value)}
                 maxLength={2} minLength={2} style={{ width: '48px' }} required />
        </div>
        <div className="campo-curto" style={{ flex: '1 1 200px' }}>
          <span className="campo-rotulo">Endereço</span>
          <input value={endereco} onChange={(e) => setEndereco(e.target.value)}
                 minLength={4} required />
        </div>
        <button type="submit" className="botao-compacto">Adicionar cinema</button>
      </form>
    </section>
  );
}

function NovaSala({ venueId, aoCriar }: { venueId: number; aoCriar: () => void }) {
  const [nome, setNome] = useState('');
  const [fileiras, setFileiras] = useState('8');
  const [porFileira, setPorFileira] = useState('12');
  const [erro, setErro] = useState<string | null>(null);

  async function criar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await organizador.criarSala(venueId, {
        name: nome,
        rows: Number(fileiras),
        seats_per_row: Number(porFileira),
      });
      setNome('');
      aoCriar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <form className="forma-inline" onSubmit={criar}>
      <div className="campo-curto">
        <span className="campo-rotulo">Nova sala</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               placeholder="Sala 3" required />
      </div>
      <div className="campo-curto">
        <span className="campo-rotulo">Fileiras</span>
        <input type="number" min={1} max={26} value={fileiras}
               onChange={(e) => setFileiras(e.target.value)}
               style={{ width: '64px' }} required />
      </div>
      <div className="campo-curto">
        <span className="campo-rotulo">Por fileira</span>
        <input type="number" min={1} max={40} value={porFileira}
               onChange={(e) => setPorFileira(e.target.value)}
               style={{ width: '64px' }} required />
      </div>
      <button type="submit" className="botao-compacto botao-compacto--vazado">
        Adicionar
      </button>
      {erro && <span className="motivo">{erro}</span>}
    </form>
  );
}
