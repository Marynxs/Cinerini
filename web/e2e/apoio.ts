/* Apoio comum aos testes: login pela tela e preparação de dados pela API.
 *
 * A regra que separa os dois: o que está sob teste passa pela interface; o
 * resto entra pelo caminho mais curto. Comprar um ingresso clicando dez vezes
 * para depois testar a portaria transformaria a falha de qualquer passo
 * anterior numa falha do teste da portaria.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';
import { API } from '../playwright.config';

export const SENHA = 'cinerini123';
export const ORGANIZADOR = 'organizador@cinerini.com.br';
export const CLIENTE = 'cliente1@cinerini.com.br';
export const CLIENTE2 = 'cliente2@cinerini.com.br';
export const PORTARIA = 'portaria@cinerini.com.br';

export const CARTAO_APROVADO = '4111111111111111';
export const CARTAO_RECUSADO = '4111111111111110';

/** Entra pela tela, usando os atalhos de conta semeada (D18). */
export async function entrar(page: Page, email: string) {
  await page.goto('/entrar');
  await page.getByRole('button', { name: email }).click();
  await page.getByLabel('Senha').fill(SENHA);

  // Dentro do formulário: "Entrar" também é o nome da aba, e o seletor solto
  // casaria com as duas.
  await page.locator('form').getByRole('button', { name: 'Entrar' }).click();
  await expect(page.getByRole('link', { name: /Meus ingressos|Painel|Portaria/ }))
    .toBeVisible();
}

/* Um token por conta, por processo.
 *
 * Sem esta memória, cada auxiliar que precisa de cabeçalho faz o próprio
 * login, e a suíte estoura o limitador de tentativas da API: oito por conta a
 * cada quinze minutos (D8). O sintoma é cruel, porque quem falha com 429 não é
 * o teste que gastou as tentativas, e sim o seguinte. */
const tokens = new Map<string, string>();

async function token(req: APIRequestContext, email: string) {
  const guardado = tokens.get(email);
  if (guardado) return guardado;

  const r = await req.post(`${API}/auth/login`, {
    data: { email, password: SENHA },
  });
  expect(r.ok(), `login de ${email} falhou: ${r.status()}`).toBeTruthy();

  const novo = (await r.json()).access_token as string;
  tokens.set(email, novo);
  return novo;
}

export async function cabecalho(req: APIRequestContext, email: string) {
  return { Authorization: `Bearer ${await token(req, email)}` };
}

/** Uma sessão que a portaria consegue assumir, para os testes de validação. */
export async function sessaoDaPortaria(req: APIRequestContext) {
  // Do escopo da própria portaria, e não do organizador: o funcionário só
  // enxerga as sessões do cinema onde trabalha (D24), e uma sessão de fora
  // não apareceria na lista de turnos da tela.
  const h = await cabecalho(req, PORTARIA);
  const r = await req.get(`${API}/gate/showings`, { headers: h });
  const turnos = await r.json();
  expect(turnos.length, 'nenhuma sessão na janela de turnos').toBeGreaterThan(0);
  return turnos[0];
}

/** Compra um ingresso pela API e devolve o código para digitar na portaria. */
export async function comprarIngresso(req: APIRequestContext, showingId: number) {
  const h = await cabecalho(req, CLIENTE);

  const assentos = await (await req.get(`${API}/showings/${showingId}/seats`)).json();
  const livre = assentos.find((a: { taken: boolean }) => !a.taken);
  expect(livre, 'sessão sem poltrona livre').toBeTruthy();

  const pedido = await (await req.post(`${API}/showings/${showingId}/reservations`, {
    headers: h, data: { seat_ids: [livre.id] },
  })).json();

  await req.post(`${API}/orders/${pedido.id}/payment`, {
    headers: h,
    data: { card_number: CARTAO_APROVADO, holder_name: 'Bruno Tavares' },
  });

  const meus = await (await req.get(`${API}/me/tickets`, { headers: h })).json();
  const alvo = meus.find((t: { id: number }) => t.id === pedido.tickets[0].id);
  return { codigo: alvo.qr_token as string, poltrona: alvo.seat_label as string };
}

/** Abre a primeira sessão do catálogo que ainda tem poltrona livre. */
export async function abrirSessaoComVaga(page: Page, req: APIRequestContext) {
  const eventos = await (await req.get(`${API}/events`)).json();
  for (const evento of eventos) {
    for (const s of evento.showings) {
      const assentos = await (await req.get(`${API}/showings/${s.id}/seats`)).json();
      if (assentos.some((a: { taken: boolean }) => !a.taken)) {
        await page.goto(`/sessoes/${s.id}`);
        return s.id as number;
      }
    }
  }
  throw new Error('nenhuma sessão com poltrona livre no catálogo semeado');
}

/** O botão de reservar dentro do resumo da compra.

    Existe um segundo botão igual na barra fixa do celular, e filtrar por
    visibilidade não os separa: para o Playwright, estar fora da dobra ainda é
    estar visível. Ancorar no resumo resolve sem ambiguidade, e a barra fixa
    tem teste próprio, onde é ela o objeto sob prova. */
export function botaoReservar(page: Page) {
  return page.getByLabel('Resumo da compra')
    .getByRole('button', { name: /^(Reservar|Atualizar reserva)$/ });
}

/** Zera o turno da portaria para que a tela sempre comece pela escolha.

    Sem isto o teste depende da ordem: uma execução anterior deixa o turno
    escolhido, a tela abre direto na câmera, e a lista que o teste procura
    não existe. */
export async function limparTurno(req: APIRequestContext, email = PORTARIA) {
  const h = await cabecalho(req, email);
  await req.put(`${API}/gate/shift`, { headers: h, data: { showing_id: null } });
}

/** Entra na portaria e assume um turno, deixando a tela pronta para validar. */
export async function entrarNaPortaria(page: Page, req: APIRequestContext) {
  const sessao = await sessaoDaPortaria(req);
  await limparTurno(req);
  await page.goto('/portaria');
  await page.getByRole('button', { name: new RegExp(sessao.event_title, 'i') })
    .first().click();
  await expect(page.getByLabel(/digite o c[óo]digo/i)).toBeVisible({ timeout: 30_000 });
  return sessao;
}

/** Caminho do arquivo de sessão gravado pelo projeto de preparação. */
export function sessaoPath(papel: string) {
  return `e2e/.auth/${papel}.json`;
}
