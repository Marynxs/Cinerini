import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { catalogo } from '../api/endpoints';
import type { CatalogEvent, City, ShowingOut } from '../api/types';
import { Carregando, Layout, Vazio } from '../components/Layout';
import './Catalog.css';

const dinheiro = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
  });

/** Sem acento e em minúscula: quem digita "sao paulo" quer achar
    "São Paulo".

    NFD separa a letra do acento, e a faixa removida é a dos sinais
    diacríticos combinantes. Escrita por código e não pelos caracteres em si,
    que são invisíveis no editor e fáceis de apagar sem querer. */
const normalizar = (texto: string) =>
  texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

/** Nome do dia e a data em si.

    "Hoje" e "Amanhã" sozinhos obrigam quem lê a calcular a data — e quem
    está escolhendo sessão quer conferir o dia, não deduzi-lo. */
function rotuloDia(iso: string): { nome: string; data: string } {
  const quando = new Date(iso);
  const hoje = new Date();
  const amanha = new Date(hoje.getTime() + 86_400_000);
  const mesmoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString();

  const data = quando.toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit',
  });

  if (mesmoDia(quando, hoje)) return { nome: 'Hoje', data };
  if (mesmoDia(quando, amanha)) return { nome: 'Amanhã', data };

  const nome = quando.toLocaleDateString('pt-BR', { weekday: 'short' })
    .replace('.', '');

  return { nome, data };
}

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit',
  });

/** Sessões de um mesmo cinema, já separadas por dia. */
interface PorCinema {
  venue: string;
  city: string;
  address: string;
  dias: [string, ShowingOut[]][];
}

function agruparPorCinema(sessoes: ShowingOut[]): PorCinema[] {
  const cinemas = new Map<string, ShowingOut[]>();

  for (const sessao of sessoes) {
    const chave = `${sessao.venue_name}|${sessao.venue_city}`;
    cinemas.set(chave, [...(cinemas.get(chave) ?? []), sessao]);
  }

  return [...cinemas.entries()].map(([chave, lista]) => {
    const [venue, city] = chave.split('|');

    const dias = new Map<string, ShowingOut[]>();
    for (const sessao of lista) {
      const dia = sessao.starts_at.slice(0, 10);
      dias.set(dia, [...(dias.get(dia) ?? []), sessao]);
    }

    return {
      venue,
      city,
      // Todas as sessões do grupo são do mesmo cinema, então qualquer uma
      // serve: o endereço pertence ao cabeçalho, não à linha da sessão.
      address: lista[0].venue_address,
      dias: [...dias.entries()].sort(([a], [b]) => a.localeCompare(b)),
    };
  }).sort((a, b) => a.venue.localeCompare(b.venue));
}

/** Filtra por título, cinema ou cidade.

    Quando o termo casa com cinema ou cidade, o filme aparece só com as
    sessões daquele lugar: mostrar todas devolveria sessões que não são o
    que a pessoa procurou. */
function filtrar(filmes: CatalogEvent[], termo: string): CatalogEvent[] {
  const busca = normalizar(termo);
  if (!busca) return filmes;

  const resultado: CatalogEvent[] = [];

  for (const filme of filmes) {
    if (normalizar(filme.title).includes(busca)) {
      resultado.push(filme);
      continue;
    }

    const sessoes = filme.showings.filter((s) =>
      normalizar(s.venue_name).includes(busca)
      || normalizar(s.venue_city).includes(busca));

    if (sessoes.length > 0) resultado.push({ ...filme, showings: sessoes });
  }

  return resultado;
}

/** Última resposta por cidade, mantida enquanto a aba viver.

    Não é cache com prazo: a busca acontece igual, toda vez. O que isto evita
    é a tela se apagar antes de ter o que colocar no lugar — voltar ao
    catálogo mostrava "Buscando sessões" sobre um vazio, e com a API
    hibernando isso vira meio minuto de tela em branco.

    Prazo de validade seria a solução errada aqui: a resposta carrega
    `seats_available`, e servir isso velho marcaria como disponível uma
    sessão já esgotada. Trocaria uma piscada por informação errada. */
const ultimaResposta = new Map<string, CatalogEvent[]>();

export function Catalog() {
  const [params, setParams] = useSearchParams();
  // O parâmetro é o código do município no IBGE, não o nome: nome de cidade
  // se repete entre estados, e filtrar por texto juntaria cidades sem
  // relação nenhuma (D23).
  const cidadeAtual = params.get('cidade');
  const chave = cidadeAtual ?? '';

  const [cidades, setCidades] = useState<City[]>([]);
  const [filmes, setFilmes] = useState<CatalogEvent[] | null>(
    () => ultimaResposta.get(chave) ?? null,
  );
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState('');

  useEffect(() => {
    catalogo.cidades().then(setCidades).catch(() => setCidades([]));
  }, []);

  useEffect(() => {
    // Sem `setFilmes(null)`: o que já está na tela continua lá até chegar
    // coisa melhor. Trocar de cidade cai no `?? null` e mostra o
    // carregamento, porque aí não há resposta anterior daquela cidade.
    setFilmes(ultimaResposta.get(chave) ?? null);
    setErro(null);

    let cancelado = false;

    catalogo.eventos(cidadeAtual ? Number(cidadeAtual) : undefined)
      .then((lista) => {
        ultimaResposta.set(chave, lista);
        // A resposta de uma cidade abandonada não pode sobrescrever a tela
        // de outra: sem isto, alternar rápido entre filtros deixa o
        // resultado da requisição mais lenta, não o da última escolhida.
        if (!cancelado) setFilmes(lista);
      })
      .catch((e: Error) => {
        if (!cancelado) setErro(e.message);
      });

    return () => { cancelado = true; };
  }, [cidadeAtual, chave]);

  const visiveis = useMemo(
    () => (filmes ? filtrar(filmes, busca) : null),
    [filmes, busca],
  );

  function escolherCidade(cidade: number | null) {
    setParams(cidade ? { cidade: String(cidade) } : {}, { replace: true });
  }

  const sessoesVisiveis = visiveis?.reduce(
    (total, f) => total + f.showings.length, 0) ?? 0;

  return (
    <Layout>
      <div className="catalogo-cabeca">
        <h1 className="catalogo-titulo">Em cartaz</h1>
        {visiveis && (
          <span className="catalogo-contagem">
            {visiveis.length} {visiveis.length === 1 ? 'filme' : 'filmes'}
            {' · '}
            {sessoesVisiveis} {sessoesVisiveis === 1 ? 'sessão' : 'sessões'}
          </span>
        )}
      </div>

      <div className="controles">
        <div className="campo-busca">
          <svg className="campo-busca-lupa" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round"
               aria-hidden="true">
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="M15.5 15.5L21 21" />
          </svg>

          <input
            type="search"
            className="campo-busca-entrada"
            placeholder="Filme, cinema ou cidade"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            aria-label="Buscar por filme, cinema ou cidade"
          />

          {busca && (
            <button
              type="button"
              className="campo-busca-limpar"
              onClick={() => setBusca('')}
              aria-label="Limpar busca"
            >
              ✕
            </button>
          )}
        </div>

        {cidades.length > 1 && (
          <div className="filtro">
            <span className="filtro-rotulo">Cidade</span>

            <button
              type="button"
              className={`cidade${!cidadeAtual ? ' cidade--ativa' : ''}`}
              onClick={() => escolherCidade(null)}
            >
              Todas
            </button>

            {cidades.map((cidade) => (
              <button
                key={cidade.id}
                type="button"
                className={`cidade${
                  cidadeAtual === String(cidade.id) ? ' cidade--ativa' : ''}`}
                onClick={() => escolherCidade(cidade.id)}
              >
                {/* A UF acompanha o nome porque cidades homônimas em estados
                    diferentes seriam indistinguíveis na lista. */}
                {cidade.nome} · {cidade.uf}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Só quando não há o que mostrar. Com o catálogo anterior na tela, uma
          atualização que falhou não justifica trocar conteúdo útil por um
          aviso — a próxima navegação tenta de novo. */}
      {erro && filmes === null && (
        <Vazio titulo="Não deu para carregar o catálogo">
          <p>{erro}</p>
        </Vazio>
      )}

      {!erro && filmes === null && <Carregando texto="Buscando sessões" />}

      {!erro && visiveis?.length === 0 && (
        <Vazio titulo="Nenhuma sessão encontrada">
          <p>
            {busca
              ? `Nada corresponde a "${busca}".`
              : cidadeAtual
                ? `Não há sessões em ${cidades.find(
                    (c) => String(c.id) === cidadeAtual)?.nome
                    ?? 'nesta cidade'} no momento.`
                : 'Não há sessões disponíveis no momento.'}
          </p>
        </Vazio>
      )}

      {visiveis && visiveis.length > 0 && (
        <div className="filmes">
          {visiveis.map((filme) => (
            <Filme key={filme.id} filme={filme} />
          ))}
        </div>
      )}
    </Layout>
  );
}

function Filme({ filme }: { filme: CatalogEvent }) {
  const cinemas = agruparPorCinema(filme.showings);

  return (
    <article className="filme">
      {filme.poster_url && (
        <img
          className="filme-poster"
          src={filme.poster_url}
          alt={`Pôster de ${filme.title}`}
          loading="lazy"
        />
      )}

      <div>
        <h2 className="filme-titulo">{filme.title}</h2>

        {filme.runtime_minutes && (
          <p className="filme-meta">{filme.runtime_minutes} min</p>
        )}

        {filme.synopsis && <Sinopse texto={filme.synopsis} />}

        <div className="cinemas">
          {cinemas.map((cinema) => (
            <section className="cinema" key={`${cinema.venue}|${cinema.city}`}>
              <h3 className="cinema-nome">
                {cinema.venue}
                <span className="cinema-cidade">{cinema.city}</span>
              </h3>

              {/* Com o mesmo filme em dois cinemas, o nome sozinho não
                  distingue qual fica perto de quem está escolhendo. */}
              <p className="cinema-endereco">{cinema.address}</p>

              {cinema.dias.map(([dia, sessoes]) => (
                <div className="sessoes-dia" key={dia}>
                  <span className="sessoes-data">
                    <span className="sessoes-data-nome">
                      {rotuloDia(sessoes[0].starts_at).nome}
                    </span>
                    <span className="sessoes-data-numero">
                      {rotuloDia(sessoes[0].starts_at).data}
                    </span>
                  </span>

                  <div className="sessoes-lista">
                    {sessoes.map((sessao) => (
                      <Sessao key={sessao.id} sessao={sessao} />
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ))}
        </div>
      </div>
    </article>
  );
}

/** Corta em três linhas e oferece o resto.

    O limite é por número de caracteres e não por medição do elemento: medir
    exigiria ler o layout depois de pintar, e o botão apareceria com um
    tremor perceptível. */
const CORTE_SINOPSE = 190;

function Sinopse({ texto }: { texto: string }) {
  const [aberta, setAberta] = useState(false);
  const longa = texto.length > CORTE_SINOPSE;

  return (
    <div className="sinopse-bloco">
      <p className={`filme-sinopse${aberta ? ' filme-sinopse--aberta' : ''}`}>
        {texto}
      </p>

      {longa && (
        <button
          type="button"
          className="sinopse-mais"
          onClick={() => setAberta((v) => !v)}
          aria-expanded={aberta}
        >
          {aberta ? 'Ver menos' : 'Ver mais'}
        </button>
      )}
    </div>
  );
}

function Sessao({ sessao }: { sessao: ShowingOut }) {
  const esgotada = sessao.seats_available <= 0;

  const conteudo = (
    <>
      <span className="sessao-hora">{hora(sessao.starts_at)}</span>
      <span className="sessao-detalhe">
        {esgotada
          ? 'Esgotada'
          : `${sessao.room_name} · ${sessao.audio} · ${dinheiro(sessao.price_cents)}`}
      </span>
    </>
  );

  if (esgotada) {
    return <span className="sessao sessao--esgotada">{conteudo}</span>;
  }

  return (
    <Link
      to={`/sessoes/${sessao.id}`}
      className="sessao"
      aria-label={
        `Sessão das ${hora(sessao.starts_at)} em ${sessao.venue_name}, `
        + `${sessao.room_name}, ${dinheiro(sessao.price_cents)}`
      }
    >
      {conteudo}
    </Link>
  );
}
