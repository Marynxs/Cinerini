/* Painel do organizador: cinemas, salas, eventos e sessões numa tela só.

   Uma tela em vez de várias porque as quatro coisas se encadeiam: não dá
   para criar sessão sem sala, nem publicar evento sem sessão, e navegar
   entre abas para completar um cadastro esconderia essa dependência. */

import { useCallback, useEffect, useState, type FormEvent } from 'react';

import { catalogo, organizador, portaria } from '../api/endpoints';
import type {
  Coverage, EventOut, Gate, Municipio, Room, ShowingBrief, ShowingOut,
  TmdbSearchResult, Uf, User, Venue,
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

type AbaId = 'eventos' | 'cinemas' | 'equipe';

const ABAS: { id: AbaId; rotulo: string }[] = [
  { id: 'eventos', rotulo: 'Eventos e sessões' },
  { id: 'cinemas', rotulo: 'Cinemas e salas' },
  { id: 'equipe', rotulo: 'Equipe' },
];

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
  const [aba, setAba] = useState<AbaId>('eventos');
  /* Sobe a cada mudança no quadro de gente. As duas seções da aba
     Equipe leem a mesma realidade por ângulos diferentes: criar um
     funcionário acrescenta um candidato à promoção, e promover tira
     alguém da lista de funcionários. Sem um sinal comum, cada uma
     ficaria mostrando o quadro de antes da ação da outra. */
  const [equipe, setEquipe] = useState(0);

  const recarregar = useCallback(async () => {
    setErro(null);
    try {
      const [cinemas, meus] = await Promise.all([
        catalogo.cinemas(),
        organizador.eventos(),
      ]);
      setVenues(cinemas);
      setEventos(meus);

      /* Salas e sessões na mesma rodada: nenhuma das duas depende da outra,
         e encadeá-las somava uma ida ao servidor que ninguém precisava
         esperar. Cada uma guarda o que trouxe assim que chega, em vez de
         esperar a outra: juntá-las num só `await` fazia o formulário de
         nova sessão dizer "cadastre um cinema" enquanto os cinemas já
         estavam na mão, presos atrás da busca mais lenta. */
      await Promise.all([
        Promise.all(cinemas.map(
          async (v) => [v.id, await catalogo.salas(v.id)] as const))
          .then((r) => setSalas(Object.fromEntries(r))),
        Promise.all(meus.map(
          async (e) => [e.id, await catalogo.sessoes(e.id)] as const))
          .then((r) => setSessoes(Object.fromEntries(r))),
      ]);
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

      {/* Abas em vez de tudo empilhado: as quatro áreas são usadas em
          momentos diferentes, já que publicar é semanal, montar portaria é
          diário e cadastrar cinema é uma vez só, e empilhá-las obrigava a rolar por
          três assuntos para chegar ao quarto. */}
      <div className="abas" role="tablist" aria-label="Áreas do painel">
        {ABAS.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            className={`aba${aba === a.id ? ' aba--ativa' : ''}`}
            onClick={() => setAba(a.id)}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`}>
        {aba === 'eventos' && (
          <>
            <NovoEvento aoCriar={recarregar} />

            <section className="painel-secao">
              <h2 className="painel-titulo">Eventos</h2>

              {eventos === null && <Carregando />}

              {eventos?.length === 0 && (
                <p className="vazio-linha">
                  Nenhum evento ainda. Busque um filme acima para criar o
                  primeiro.
                </p>
              )}

              {eventos?.map((evento) => (
                <Evento
                  key={evento.id}
                  evento={evento}
                  sessoes={sessoes[evento.id]}
                  salas={todasSalas}
                  venues={venues}
                  aoMudar={recarregar}
                />
              ))}
            </section>
          </>
        )}

        {aba === 'cinemas' && (
          <Cinemas venues={venues} salas={salas} aoMudar={recarregar} />
        )}

        {aba === 'equipe' && (
          <>
            <Portarias
              venues={venues}
              versao={equipe}
              aoMudar={() => setEquipe((n) => n + 1)}
            />
            <Organizadores
              versao={equipe}
              aoMudar={() => setEquipe((n) => n + 1)}
            />
          </>
        )}
      </div>
    </Layout>
  );
}

/* --------------------------------------------- portarias e equipe */

/** Contas de portaria: uma pessoa, um cinema.

    Fica no painel do organizador porque portaria não se auto-cadastra: o
    papel decide quem entra na sala, e concedê-lo pelo formulário público
    deixaria qualquer visitante abrir a porta.

    O que se define aqui é o **cinema**, que é o escopo do emprego. Qual
    sessão a pessoa atende é escolha dela, a cada turno, na própria tela da
    portaria (D24). */
interface EquipeProps {
  versao: number;
  aoMudar: () => void;
}

function Portarias({ venues, versao, aoMudar }: EquipeProps & { venues: Venue[] }) {
  const [gates, setGates] = useState<Gate[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [venueId, setVenueId] = useState('');

  const [editando, setEditando] = useState<number | null>(null);
  const [removendo, setRemovendo] = useState<Gate | null>(null);

  /* Sessões que cada cinema pode oferecer, para o seletor de escala.

     Vem da cobertura, que já traz as sessões da janela em que alguém pode
     assumir, e buscar de novo por outro caminho daria duas listas com
     prazos possivelmente diferentes (D26). */
  const [turnosPorCinema, setTurnosPorCinema] =
    useState<Record<number, ShowingBrief[]>>({});

  const recarregar = useCallback(() => {
    portaria.listar().then(setGates).catch((e: Error) => setErro(e.message));

    portaria.cobertura().then((cob) => {
      const porCinema: Record<number, ShowingBrief[]> = {};
      for (const c of cob) {
        const cinema = venues.find((v) => v.name === c.showing.venue_name);
        if (!cinema) continue;
        porCinema[cinema.id] = [...(porCinema[cinema.id] ?? []), c.showing];
      }
      setTurnosPorCinema(porCinema);
    }).catch(() => setTurnosPorCinema({}));
  }, [venues]);

  async function escalar(alvo: Gate, valor: string) {
    setErro(null);
    try {
      await portaria.editar(alvo.id,
                            { showing_id: valor ? Number(valor) : null });
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  async function remover(alvo: Gate) {
    setErro(null);
    try {
      await portaria.remover(alvo.id);
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  useEffect(recarregar, [recarregar, versao]);

  async function criar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await portaria.criar(Number(venueId), {
        name: nome, email, password: senha,
      });
      setNome(''); setEmail(''); setSenha(''); setVenueId('');
      // Avisa a seção de promoção: o novo funcionário já é candidato.
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section className="painel-secao">
      <h2 className="painel-titulo">Funcionários</h2>

      {erro && <p className="motivo">{erro}</p>}

      <Cobertura versao={versao} />

      {gates === null && <Carregando />}

      {gates?.length === 0 && (
        <p className="vazio-linha">
          Nenhum funcionário cadastrado. Crie um abaixo para validar
          ingressos na entrada.
        </p>
      )}

      {gates && gates.length > 0 && (
        <table className="tabela">
          <thead>
            <tr>
              <th>Funcionário</th>
              <th>Acesso</th>
              <th>Cinema</th>
              <th>Atendendo agora</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {gates.map((g) => (
              <tr key={g.id}>
                <td>{g.name}</td>
                <td className="portaria-email">{g.email}</td>
                <td>{g.venue_name ?? <span className="motivo">sem cinema</span>}</td>
                <td>
                  {/* Editável, e não só informativo. O caminho normal
                      continua sendo o funcionário escolher na própria tela
                      (D24); isto é o remanejamento de quem coordena a
                      noite, sem depender de ele estar com o aparelho na
                      mão. */}
                  <select
                    className="portaria-vinculo"
                    value={g.showing_id ?? ''}
                    disabled={g.venue_id === null}
                    onChange={(e) => escalar(g, e.target.value)}
                  >
                    <option value="">Fora de turno</option>
                    {(turnosPorCinema[g.venue_id ?? 0] ?? []).map((s) => (
                      <option key={s.showing_id} value={s.showing_id ?? ''}>
                        {s.event_title} · {quando(s.starts_at)} · {s.room_name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="tabela-acoes">
                  <button type="button" className="elo"
                          onClick={() => setEditando(
                            editando === g.id ? null : g.id)}>
                    {editando === g.id ? 'Cancelar' : 'Editar'}
                  </button>
                  <button type="button" className="elo elo--perigo"
                          onClick={() => setRemovendo(g)}>
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="forma-inline" onSubmit={criar}>
        <label className="campo-curto">
          <span className="campo-rotulo">Novo funcionário</span>
          <input value={nome} onChange={(e) => setNome(e.target.value)}
                 placeholder="Nome da pessoa" minLength={2} required />
        </label>

        <label className="campo-curto">
          <span className="campo-rotulo">E-mail de acesso</span>
          <input type="email" value={email} autoComplete="off" required
                 onChange={(e) => setEmail(e.target.value)} />
        </label>

        <label className="campo-curto">
          <span className="campo-rotulo">Senha (mín. 8)</span>
          <input type="password" value={senha} minLength={8} required
                 autoComplete="new-password"
                 onChange={(e) => setSenha(e.target.value)} />
        </label>

        <label className="campo-curto portaria-escolha">
          <span className="campo-rotulo">Cinema onde trabalha</span>
          <select value={venueId} required
                  onChange={(e) => setVenueId(e.target.value)}>
            <option value="" disabled>Escolha o cinema</option>
            {venues.map((v) => (
              <option key={v.id} value={v.id}>{v.name} · {v.city}</option>
            ))}
          </select>
        </label>

        <button type="submit" className="botao-compacto"
                disabled={salvando || !venueId}>
          {salvando ? 'Criando…' : 'Criar funcionário'}
        </button>
      </form>

      {editando !== null && gates?.some((g) => g.id === editando) && (
        <EditarFuncionario
          gate={gates.find((g) => g.id === editando)!}
          venues={venues}
          aoSalvar={() => { setEditando(null); aoMudar(); }}
        />
      )}

      {removendo && (
        <Confirmar
          titulo="Remover funcionário"
          rotuloConfirmar="Remover funcionário"
          aoFechar={() => setRemovendo(null)}
          aoConfirmar={() => {
            const alvo = removendo; setRemovendo(null); remover(alvo);
          }}
        >
          <p>
            <span className="dialogo-destaque">{removendo.name}</span>
            {' · '}{removendo.email}
          </p>
          <p className="dialogo-consequencia">
            A conta deixa de existir e não entra mais no sistema. Quem já
            validou ingressos não pode ser removido, porque o histórico deixaria de
            dizer quem estava na porta. Esta ação é irreversível.
          </p>
        </Confirmar>
      )}
    </section>
  );
}

/** Edição de um organizador: só o nome.

    E-mail e senha são identidade da pessoa, não cadastro. Trocar o e-mail
    pelo painel mudaria a credencial de alguém sem que ele soubesse (D27). */
function EditarOrganizador(
  { alvo, aoSalvar }: { alvo: User; aoSalvar: () => void },
) {
  const [nome, setNome] = useState(alvo.name);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await organizador.editarOrganizador(alvo.id, nome);
      aoSalvar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form className="forma-inline" onSubmit={salvar}>
      {erro && <p className="motivo">{erro}</p>}

      <label className="campo-curto" style={{ flex: '1 1 200px' }}>
        <span className="campo-rotulo">Nome</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               minLength={2} required />
      </label>

      <button type="submit" className="botao-compacto" disabled={salvando}>
        {salvando ? 'Salvando…' : 'Salvar'}
      </button>

      <span className="campo-ajuda">
        E-mail e senha pertencem à pessoa e não se editam por aqui.
      </span>
    </form>
  );
}

/** Sessões que começam em breve e quem está na porta de cada uma.

    Existe porque a tabela abaixo responde a pergunta errada. Ela diz o que
    cada funcionário atende; quem opera um cinema precisa do contrário: se a
    sessão das 21:30 tem alguém. Cruzar as duas colunas na cabeça funciona
    com três funcionários e falha numa noite cheia, e o erro só aparece
    quando a fila já se formou (D26).

    O carmim aqui é uso legítimo: sessão descoberta é atenção, não enfeite. */
function Cobertura({ versao }: { versao: number }) {
  const [lista, setLista] = useState<Coverage[] | null>(null);

  useEffect(() => {
    portaria.cobertura().then(setLista).catch(() => setLista([]));
  }, [versao]);

  if (lista === null || lista.length === 0) return null;

  const descobertas = lista.filter((c) => c.staff.length === 0);

  return (
    <div className="cobertura">
      <p className="cobertura-titulo">
        Próximas sessões · {descobertas.length === 0
          ? 'todas com alguém na porta'
          : `${descobertas.length} sem ninguém na porta`}
      </p>

      <ul className="cobertura-lista">
        {lista.map((c) => (
          <li
            key={c.showing.showing_id}
            className={`cobertura-item${
              c.staff.length === 0 ? ' cobertura-item--vazia' : ''}`}
          >
            <span className="cobertura-quando">
              {quando(c.showing.starts_at)}
            </span>
            <span className="cobertura-sessao">
              {c.showing.event_title} · {c.showing.room_name}
            </span>
            {/* O organizador vem marcado: ele cobre a porta pelo próprio
                papel (D27), mas não é funcionário alocado, e quem lê precisa
                saber que aquela sessão está coberta por quem também
                administra, e não por alguém da escala (D33). */}
            <span className="cobertura-quem">
              {c.staff.length === 0 ? 'sem ninguém' : c.staff.map((p) => (
                <span key={p.name} className="cobertura-pessoa">
                  {p.name}
                  {p.organizer && (
                    <span className="cobertura-papel"> · organizador</span>
                  )}
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Edição de um funcionário: nome e cinema.

    A senha não entra: trocá-la pelo painel obrigaria a entregar a nova por
    algum canal, e senha que trafega por mensagem fica no histórico de
    alguém (D22). */
function EditarFuncionario(
  { gate, venues, aoSalvar }:
  { gate: Gate; venues: Venue[]; aoSalvar: () => void },
) {
  const [nome, setNome] = useState(gate.name);
  const [venueId, setVenueId] = useState(
    gate.venue_id === null ? '' : String(gate.venue_id));
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await portaria.editar(gate.id, {
        name: nome,
        venue_id: venueId === '' ? null : Number(venueId),
      });
      aoSalvar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form className="forma-inline" onSubmit={salvar}>
      {erro && <p className="motivo">{erro}</p>}

      <label className="campo-curto" style={{ flex: '1 1 160px' }}>
        <span className="campo-rotulo">Nome</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               minLength={2} required />
      </label>

      <label className="campo-curto portaria-escolha">
        <span className="campo-rotulo">Cinema onde trabalha</span>
        <select value={venueId} onChange={(e) => setVenueId(e.target.value)}>
          <option value="">Sem cinema, não valida nada</option>
          {venues.map((v) => (
            <option key={v.id} value={v.id}>{v.name} · {v.city}</option>
          ))}
        </select>
      </label>

      <button type="submit" className="botao-compacto" disabled={salvando}>
        {salvando ? 'Salvando…' : 'Salvar'}
      </button>

      <span className="campo-ajuda">
        Trocar de cinema encerra o turno em andamento.
      </span>
    </form>
  );
}

/** Quem mais pode publicar eventos.

    Promoção e não criação: a conta e a senha já são da pessoa. Criá-la aqui
    obrigaria o organizador a inventar uma senha e mandá-la por algum canal,
    e senha que trafega por mensagem fica no histórico de alguém (D22). */
function Organizadores({ versao, aoMudar }: EquipeProps) {
  const [lista, setLista] = useState<User[] | null>(null);
  const [candidatos, setCandidatos] = useState<Gate[]>([]);
  const [email, setEmail] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [editando, setEditando] = useState<number | null>(null);
  const [revogando, setRevogando] = useState<User | null>(null);

  async function revogar(alvo: User) {
    setErro(null);
    try {
      await organizador.revogarOrganizador(alvo.id);
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  /* Promover é escolher numa lista, não digitar o e-mail. Digitar exige
     saber de cor o endereço com que a pessoa se cadastrou, e erra calado:
     um caractere trocado devolve "conta não encontrada" sem dizer qual era
     a certa. */
  const recarregar = useCallback(() => {
    organizador.organizadores().then(setLista)
      .catch((e: Error) => setErro(e.message));
    portaria.listar().then(setCandidatos).catch(() => setCandidatos([]));
  }, []);

  useEffect(recarregar, [recarregar, versao]);

  async function promover(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await organizador.promover(email);
      setEmail('');
      // A lista de funcionários encolheu: quem foi promovido deixa de ser
      // funcionário, e a seção acima precisa refletir isso.
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section className="painel-secao">
      <h2 className="painel-titulo">Organizadores</h2>

      {erro && <p className="motivo">{erro}</p>}

      {lista === null && <Carregando />}

      {lista && (
        <table className="tabela">
          <thead>
            <tr><th>Nome</th><th>E-mail</th><th /></tr>
          </thead>
          <tbody>
            {lista.map((o) => {
              // O primeiro organizador é o de menor id: é ele que impede a
              // instalação de ficar sem ninguém que publique (D27).
              const primeiro = o.id === Math.min(...lista.map((x) => x.id));

              return (
                <tr key={o.id}>
                  <td>
                    {o.name}
                    {primeiro && (
                      <span className="selo-primeiro" title="Primeiro organizador">
                        fundador
                      </span>
                    )}
                  </td>
                  <td className="portaria-email">{o.email}</td>
                  <td className="tabela-acoes">
                    <button type="button" className="elo"
                            onClick={() => setEditando(
                              editando === o.id ? null : o.id)}>
                      {editando === o.id ? 'Cancelar' : 'Editar'}
                    </button>
                    {!primeiro && (
                      <button type="button" className="elo elo--perigo"
                              onClick={() => setRevogando(o)}>
                        Revogar
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {editando !== null && lista?.some((o) => o.id === editando) && (
        <EditarOrganizador
          alvo={lista.find((o) => o.id === editando)!}
          aoSalvar={() => { setEditando(null); aoMudar(); }}
        />
      )}

      {revogando && (
        <Confirmar
          titulo="Revogar organizador"
          rotuloConfirmar="Revogar papel"
          aoFechar={() => setRevogando(null)}
          aoConfirmar={() => {
            const alvo = revogando; setRevogando(null); revogar(alvo);
          }}
        >
          <p>
            <span className="dialogo-destaque">{revogando.name}</span>
            {' · '}{revogando.email}
          </p>
          <p className="dialogo-consequencia">
            A conta volta a ser de funcionário, sem cinema definido. Escolha
            um na seção <em>Funcionários</em> para que ela possa validar de
            novo. Os eventos que ela publicou seguem no ar: apagar levaria
            junto sessões e ingressos vendidos.
          </p>
        </Confirmar>
      )}

      {candidatos.length === 0 ? (
        <p className="vazio-linha">
          Nenhum funcionário para promover. Cadastre um na seção acima.
        </p>
      ) : (
        <form className="forma-inline" onSubmit={promover}>
          <label className="campo-curto portaria-escolha">
            <span className="campo-rotulo">Promover funcionário a organizador</span>
            <select value={email} required
                    onChange={(e) => setEmail(e.target.value)}>
              <option value="" disabled>Escolha o funcionário</option>
              {candidatos.map((c) => (
                <option key={c.id} value={c.email}>
                  {c.name}{c.venue_name ? ` · ${c.venue_name}` : ''}
                </option>
              ))}
            </select>
          </label>

          <button type="submit" className="botao-compacto"
                  disabled={salvando || !email}>
            {salvando ? 'Promovendo…' : 'Promover'}
          </button>
        </form>
      )}

      <p className="vazio-linha">
        Quem é promovido deixa de ser funcionário: os papéis são exclusivos, e
        quem publica sessões não continua validando na porta.
      </p>
    </section>
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
        <label className="campo-curto" style={{ flex: '1 1 260px' }}>
          <span className="campo-rotulo">Título do filme</span>
          <input
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Duna, Matrix, Cidade de Deus…"
            minLength={2}
            required
          />
        </label>
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
  /** `undefined` enquanto a busca não voltou; `[]` é evento sem sessão. */
  sessoes: ShowingOut[] | undefined;
  salas: Room[];
  venues: Venue[];
  aoMudar: () => void;
}

function Evento({ evento, sessoes, salas, venues, aoMudar }: EventoProps) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aCancelar, setACancelar] = useState<ShowingOut | null>(null);
  const [aApagarSessao, setAApagarSessao] = useState<ShowingOut | null>(null);
  const [aApagar, setAApagar] = useState(false);

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
  /* Lista ausente e lista vazia diziam a mesma coisa na tela, e a tela
     afirmava "nenhuma sessão cadastrada" durante os segundos em que ainda
     estava buscando. Zero que significa "não sei" é o mesmo defeito que a
     ocupação 0/0 tinha. */
  const carregando = sessoes === undefined;
  const lista = sessoes ?? [];

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

          {/* Sempre visível, inclusive quando não dá. Escondê-lo enquanto
              o evento estava publicado ou tinha sessão fazia a remoção
              parecer inexistente, e quem queria tirar um filme do ar não
              tinha como descobrir que o caminho é despublicar, esvaziar e
              então apagar. Clicável de propósito: é o clique que responde
              qual dos dois passos ainda falta (D30). */}
          <button
            type="button"
            className="elo elo--perigo"
            aria-disabled={publicado || carregando || lista.length > 0}
            onClick={() => {
              if (carregando) {
                setErro('As sessões deste evento ainda estão carregando.');
              } else if (publicado) {
                setErro('Evento publicado não é apagado direto: enquanto '
                  + 'está no ar ele pode estar vendendo. Despublique '
                  + 'primeiro.');
              } else if (lista.length > 0) {
                setErro(`Este rascunho ainda tem ${lista.length} `
                  + 'sessão(ões). Apague as sessões da tabela acima antes.');
              } else {
                setErro(null);
                setAApagar(true);
              }
            }}
          >
            Apagar evento
          </button>

          <button
            type="button"
            className="botao-compacto botao-compacto--vazado"
            disabled={ocupado || carregando
              || (!publicado && lista.length === 0)}
            title={!publicado && !carregando && lista.length === 0
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

      {carregando ? (
        <Carregando aviso={false} />
      ) : lista.length === 0 ? (
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
            {lista.map((s) => {
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
                  <td className="tabela-acoes">
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
                    {/* Apagar só aparece quando não resta ingresso a avisar.
                        Com venda viva o caminho é cancelar antes, e oferecer
                        os dois lado a lado convidaria a escolher justamente
                        o que não informa quem comprou (D36). */}
                    {(cancelada || vendidos === 0) && (
                      <button
                        type="button"
                        className="elo elo--perigo"
                        disabled={ocupado}
                        onClick={() => setAApagarSessao(s)}
                      >
                        Apagar
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

      {aApagar && (
        <Confirmar
          titulo="Apagar evento"
          rotuloConfirmar="Apagar evento"
          aoFechar={() => setAApagar(false)}
          aoConfirmar={() => {
            setAApagar(false);
            agir(() => organizador.removerEvento(evento.id));
          }}
        >
          <p><span className="dialogo-destaque">{evento.title}</span></p>
          <p className="dialogo-consequencia">
            O filme sai do catálogo do painel. Como não está publicado e não
            tem sessões, ninguém comprou nada nele. Esta ação é irreversível.
          </p>
        </Confirmar>
      )}

      {aApagarSessao && (
        <Confirmar
          titulo="Apagar sessão"
          rotuloConfirmar="Apagar sessão"
          aoFechar={() => setAApagarSessao(null)}
          aoConfirmar={() => {
            const sessao = aApagarSessao;
            setAApagarSessao(null);
            agir(() => organizador.removerSessao(sessao.id));
          }}
        >
          <p>
            <span className="dialogo-destaque">{evento.title}</span>
            {' · '}{quando(aApagarSessao.starts_at)}
            {' · '}{aApagarSessao.venue_name}, {aApagarSessao.room_name}
          </p>
          <p className="dialogo-consequencia">
            {aApagarSessao.cancelled_at
              ? 'A sessão já está cancelada. Apagar leva junto o mapa de '
                + 'poltronas e os ingressos estornados, e quem comprou '
                + 'deixa de ver o motivo em Meus ingressos.'
              : 'Nenhum ingresso vendido: a sessão sai do sistema sem '
                + 'afetar ninguém.'}
            {' '}Esta ação é irreversível.
          </p>
        </Confirmar>
      )}

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
      <label className="campo-curto">
        <span className="campo-rotulo">Sala</span>
        <select value={roomId} onChange={(e) => setRoomId(e.target.value)} required>
          <option value="">Escolha</option>
          {salas.map((sala) => (
            <option key={sala.id} value={sala.id}>
              {venues.find((v) => v.id === sala.venue_id)?.name} · {sala.name}
            </option>
          ))}
        </select>
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Data</span>
        <input
          type="date"
          value={data}
          onChange={(e) => setData(e.target.value)}
          className="campo-data"
          required
        />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Horário</span>
        <input
          type="time"
          value={hora}
          onChange={(e) => setHora(e.target.value)}
          className="campo-hora"
          required
        />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Preço</span>
        <input
          value={preco}
          onChange={(e) => setPreco(e.target.value)}
          style={{ width: '80px' }}
          required
        />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Áudio</span>
        <select value={audio} onChange={(e) => setAudio(e.target.value)}>
          <option>Dublado</option>
          <option>Legendado</option>
        </select>
      </label>

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
  const [uf, setUf] = useState('');
  const [cidadeId, setCidadeId] = useState('');
  const [endereco, setEndereco] = useState('');

  /* Cidade e UF escolhidas em lista, nunca digitadas: eram texto livre, e o
     filtro do catálogo agrupa cinemas por cidade, e "São Paulo" e "sao paulo"
     viravam duas cidades, e nenhuma validação de formato pega isso (D23).

     As UFs vêm de uma constante no servidor; os municípios, do IBGE. */
  const [ufs, setUfs] = useState<Uf[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[] | null>(null);

  // Um id de cada vez: dois formulários abertos ao mesmo tempo deixariam
  // ambíguo qual deles o botão de salvar atende.
  const [editando, setEditando] = useState<number | null>(null);
  const [salaEditando, setSalaEditando] = useState<number | null>(null);
  const [removendo, setRemovendo] = useState<Venue | null>(null);
  const [salaRemovendo, setSalaRemovendo] = useState<Room | null>(null);

  async function remover(alvo: Venue) {
    setErro(null);
    try {
      await organizador.removerCinema(alvo.id);
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  async function removerSala(alvo: Room) {
    setErro(null);
    try {
      await organizador.removerSala(alvo.venue_id, alvo.id);
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  useEffect(() => {
    catalogo.ufs().then(setUfs).catch(() => setUfs([]));
  }, []);

  useEffect(() => {
    setCidadeId('');
    if (!uf) { setMunicipios(null); return; }

    setMunicipios(null);
    catalogo.municipios(uf)
      .then(setMunicipios)
      .catch((e: Error) => { setMunicipios([]); setErro(e.message); });
  }, [uf]);

  async function criarCinema(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await organizador.criarCinema({
        name: nome, state: uf, city_ibge_id: Number(cidadeId),
        address: endereco,
      });
      setNome(''); setUf(''); setCidadeId(''); setEndereco('');
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

            <span className="linha-acoes">
              <button type="button" className="elo"
                      onClick={() => setEditando(
                        editando === venue.id ? null : venue.id)}>
                {editando === venue.id ? 'Cancelar' : 'Editar'}
              </button>
              <button type="button" className="elo elo--perigo"
                      onClick={() => setRemovendo(venue)}>
                Remover
              </button>
            </span>
          </div>

          {editando === venue.id && (
            <EditarCinema
              venue={venue}
              ufs={ufs}
              aoSalvar={() => { setEditando(null); aoMudar(); }}
            />
          )}

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
                  <th />
                </tr>
              </thead>
              <tbody>
                {salas[venue.id].map((sala) => (
                  <tr key={sala.id}>
                    <td>{sala.name}</td>
                    <td className="tabela-num">{sala.rows}</td>
                    <td className="tabela-num">{sala.seats_per_row}</td>
                    <td className="tabela-num">{sala.capacity}</td>
                    <td className="tabela-acoes">
                      <button type="button" className="elo"
                              onClick={() => setSalaEditando(
                                salaEditando === sala.id ? null : sala.id)}>
                        {salaEditando === sala.id ? 'Cancelar' : 'Editar'}
                      </button>
                      <button type="button" className="elo elo--perigo"
                              onClick={() => setSalaRemovendo(sala)}>
                        Remover
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {salaEditando !== null
            && salas[venue.id]?.some((s) => s.id === salaEditando) && (
            <EditarSala
              sala={salas[venue.id].find((s) => s.id === salaEditando)!}
              aoSalvar={() => { setSalaEditando(null); aoMudar(); }}
            />
          )}

          <NovaSala venueId={venue.id} aoCriar={aoMudar} />
        </article>
      ))}

      <form className="forma-inline" onSubmit={criarCinema}
            style={{ border: 'none', paddingLeft: 0 }}>
        <label className="campo-curto">
          <span className="campo-rotulo">Novo cinema</span>
          <input value={nome} onChange={(e) => setNome(e.target.value)}
                 placeholder="Nome" minLength={2} required />
        </label>
        <label className="campo-curto">
          <span className="campo-rotulo">UF</span>
          <select value={uf} onChange={(e) => setUf(e.target.value)} required>
            <option value="" disabled>UF</option>
            {ufs.map((u) => (
              <option key={u.sigla} value={u.sigla}>{u.sigla}</option>
            ))}
          </select>
        </label>
        <label className="campo-curto" style={{ flex: '1 1 200px' }}>
          <span className="campo-rotulo">Cidade</span>
          <select value={cidadeId} required disabled={!uf || municipios === null}
                  onChange={(e) => setCidadeId(e.target.value)}>
            <option value="" disabled>
              {!uf ? 'Escolha a UF primeiro'
                : municipios === null ? 'Carregando…'
                  : 'Escolha a cidade'}
            </option>
            {(municipios ?? []).map((m) => (
              <option key={m.id} value={m.id}>{m.nome}</option>
            ))}
          </select>
        </label>
        <label className="campo-curto" style={{ flex: '1 1 200px' }}>
          <span className="campo-rotulo">Endereço</span>
          <input value={endereco} onChange={(e) => setEndereco(e.target.value)}
                 minLength={4} required />
        </label>
        <button type="submit" className="botao-compacto" disabled={!cidadeId}>
          Adicionar cinema
        </button>
      </form>

      {removendo && (
        <Confirmar
          titulo="Remover cinema"
          rotuloConfirmar="Remover cinema"
          aoFechar={() => setRemovendo(null)}
          aoConfirmar={() => { const alvo = removendo; setRemovendo(null); remover(alvo); }}
        >
          <p>
            <span className="dialogo-destaque">{removendo.name}</span>
            {' · '}{removendo.city} · {removendo.state}
          </p>
          <p className="dialogo-consequencia">
            O cinema sai do cadastro. Contas de funcionário ligadas a ele
            ficam sem cinema e param de validar. Esta ação é irreversível.
          </p>
        </Confirmar>
      )}

      {salaRemovendo && (
        <Confirmar
          titulo="Remover sala"
          rotuloConfirmar="Remover sala"
          aoFechar={() => setSalaRemovendo(null)}
          aoConfirmar={() => {
            const alvo = salaRemovendo; setSalaRemovendo(null); removerSala(alvo);
          }}
        >
          <p>
            <span className="dialogo-destaque">{salaRemovendo.name}</span>
            {' · '}{salaRemovendo.capacity} lugares
          </p>
          <p className="dialogo-consequencia">
            Sala com sessões agendadas não pode ser removida. Esta ação é
            irreversível.
          </p>
        </Confirmar>
      )}
    </section>
  );
}

/** Edição de uma sala.

    O layout continua editável mesmo com sessões marcadas: os assentos
    pertencem à exibição e são gerados na publicação (D6), então a mudança
    vale para as próximas e não reescreve mapa já vendido. */
function EditarSala(
  { sala, aoSalvar }: { sala: Room; aoSalvar: () => void },
) {
  const [nome, setNome] = useState(sala.name);
  const [fileiras, setFileiras] = useState(String(sala.rows));
  const [porFileira, setPorFileira] = useState(String(sala.seats_per_row));
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await organizador.editarSala(sala.venue_id, sala.id, {
        name: nome, rows: Number(fileiras), seats_per_row: Number(porFileira),
      });
      aoSalvar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form className="forma-inline" onSubmit={salvar}>
      {erro && <p className="motivo">{erro}</p>}

      <label className="campo-curto" style={{ flex: '1 1 140px' }}>
        <span className="campo-rotulo">Sala</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               minLength={1} required />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Fileiras</span>
        <input type="number" min={1} max={26} value={fileiras}
               style={{ width: '72px' }} required
               onChange={(e) => setFileiras(e.target.value)} />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">Por fileira</span>
        <input type="number" min={1} max={40} value={porFileira}
               style={{ width: '72px' }} required
               onChange={(e) => setPorFileira(e.target.value)} />
      </label>

      <button type="submit" className="botao-compacto" disabled={salvando}>
        {salvando ? 'Salvando…' : 'Salvar'}
      </button>

      <span className="campo-ajuda">
        Vale para as próximas sessões; mapas já gerados não mudam.
      </span>
    </form>
  );
}

/** Edição de um cinema, aberta na própria linha.

    A cidade só muda em par com a UF: mandar uma sem a outra deixaria o
    código do município apontando para outro estado (D23). */
function EditarCinema(
  { venue, ufs, aoSalvar }: { venue: Venue; ufs: Uf[]; aoSalvar: () => void },
) {
  const [nome, setNome] = useState(venue.name);
  const [endereco, setEndereco] = useState(venue.address);
  const [uf, setUf] = useState(venue.state);
  const [cidadeId, setCidadeId] = useState(String(venue.city_ibge_id));
  const [municipios, setMunicipios] = useState<Municipio[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    catalogo.municipios(uf).then(setMunicipios).catch(() => setMunicipios([]));
  }, [uf]);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await organizador.editarCinema(venue.id, {
        name: nome, address: endereco,
        state: uf, city_ibge_id: Number(cidadeId),
      });
      aoSalvar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form className="forma-inline" onSubmit={salvar}>
      {erro && <p className="motivo">{erro}</p>}

      <label className="campo-curto" style={{ flex: '1 1 160px' }}>
        <span className="campo-rotulo">Nome</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               minLength={2} required />
      </label>

      <label className="campo-curto">
        <span className="campo-rotulo">UF</span>
        <select value={uf} onChange={(e) => { setUf(e.target.value); setCidadeId(''); }}>
          {ufs.map((u) => <option key={u.sigla} value={u.sigla}>{u.sigla}</option>)}
        </select>
      </label>

      <label className="campo-curto" style={{ flex: '1 1 180px' }}>
        <span className="campo-rotulo">Cidade</span>
        <select value={cidadeId} required disabled={municipios === null}
                onChange={(e) => setCidadeId(e.target.value)}>
          <option value="" disabled>
            {municipios === null ? 'Carregando…' : 'Escolha a cidade'}
          </option>
          {(municipios ?? []).map((m) => (
            <option key={m.id} value={m.id}>{m.nome}</option>
          ))}
        </select>
      </label>

      <label className="campo-curto" style={{ flex: '1 1 200px' }}>
        <span className="campo-rotulo">Endereço</span>
        <input value={endereco} onChange={(e) => setEndereco(e.target.value)}
               minLength={4} required />
      </label>

      <button type="submit" className="botao-compacto"
              disabled={salvando || !cidadeId}>
        {salvando ? 'Salvando…' : 'Salvar'}
      </button>
    </form>
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
      <label className="campo-curto">
        <span className="campo-rotulo">Nova sala</span>
        <input value={nome} onChange={(e) => setNome(e.target.value)}
               placeholder="Sala 3" required />
      </label>
      <label className="campo-curto">
        <span className="campo-rotulo">Fileiras</span>
        <input type="number" min={1} max={26} value={fileiras}
               onChange={(e) => setFileiras(e.target.value)}
               style={{ width: '64px' }} required />
      </label>
      <label className="campo-curto">
        <span className="campo-rotulo">Por fileira</span>
        <input type="number" min={1} max={40} value={porFileira}
               onChange={(e) => setPorFileira(e.target.value)}
               style={{ width: '64px' }} required />
      </label>
      <button type="submit" className="botao-compacto botao-compacto--vazado">
        Adicionar
      </button>
      {erro && <span className="motivo">{erro}</span>}
    </form>
  );
}
