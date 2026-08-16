/* Cliente HTTP.

   Camada única entre as telas e a API: nenhuma tela chama fetch direto. É o
   que permite tratar token, erro e hibernação do servidor num lugar só.
*/

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const CHAVE_TOKEN = 'cinerini.token';

/** Erro com a mensagem que a API mandou, pronta para a tela exibir.

    Os campos são atribuídos no corpo do construtor, e não declarados nos
    parâmetros: o projeto usa `erasableSyntaxOnly`, que só admite sintaxe
    que desaparece ao remover os tipos. */
export class ApiError extends Error {
  status: number;
  /** Poltronas perdidas numa disputa, quando a API as devolve. */
  seats: string[];

  constructor(status: number, message: string, seats: string[] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.seats = seats;
  }
}

export const token = {
  get: () => localStorage.getItem(CHAVE_TOKEN),
  set: (valor: string) => localStorage.setItem(CHAVE_TOKEN, valor),
  clear: () => localStorage.removeItem(CHAVE_TOKEN),
};

/* O detail da API vem em três formas: texto simples, objeto com mensagem e
   poltronas, ou a lista de erros de validação do FastAPI. */
function extrairErro(status: number, corpo: unknown): ApiError {
  const detail = (corpo as { detail?: unknown })?.detail;

  if (typeof detail === 'string') return new ApiError(status, detail);

  if (detail && typeof detail === 'object' && 'message' in detail) {
    const d = detail as { message: string; seats?: string[] };
    return new ApiError(status, d.message, d.seats ?? []);
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const primeiro = detail[0] as { msg?: string };
    return new ApiError(status, primeiro.msg ?? 'Dados inválidos.');
  }

  return new ApiError(status, 'Não foi possível concluir. Tente de novo.');
}

interface Opcoes {
  method?: string;
  body?: unknown;
  /** Rotas públicas não mandam token nem deslogam em 401. */
  publica?: boolean;
}

export async function request<T>(
  caminho: string, { method = 'GET', body, publica }: Opcoes = {},
): Promise<T> {
  const cabecalhos: Record<string, string> = {};
  const guardado = token.get();

  if (body !== undefined) cabecalhos['Content-Type'] = 'application/json';
  if (guardado && !publica) cabecalhos.Authorization = `Bearer ${guardado}`;

  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method,
      headers: cabecalhos,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // Falha de rede não tem status. A mensagem precisa distinguir "o
    // servidor recusou" de "não consegui falar com o servidor".
    throw new ApiError(0, 'Não foi possível falar com o servidor.');
  }

  if (resposta.status === 401 && !publica) {
    // Token expirado ou revogado: limpar aqui evita a tela repetir a
    // requisição em laço achando que ainda está autenticada.
    token.clear();
  }

  if (resposta.status === 204) return undefined as T;

  const corpo = await resposta.json().catch(() => null);

  if (!resposta.ok) throw extrairErro(resposta.status, corpo);

  return corpo as T;
}

/** Acorda a API antes de o cliente precisar dela.

    O plano gratuito do Render hiberna após inatividade, e religar leva
    dezenas de segundos. Chamar /health assim que a página abre gasta esse
    tempo enquanto a pessoa ainda está lendo a tela, em vez de deixá-la
    esperando depois do primeiro clique.

    Falha em silêncio de propósito: é otimização, não requisito. */
export function aquecer(): void {
  fetch(`${BASE}/health`).catch(() => {});
}
