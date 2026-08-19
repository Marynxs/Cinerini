/* Percurso guiado do sistema inteiro, com captura de cada estado.
 *
 * Não substitui as outras suítes: elas provam comportamento, esta documenta.
 * Cada passo grava uma imagem em `e2e/capturas/<projeto>/`, incluindo os
 * estados de erro, que são metade do que este sistema tem de interessante.
 *
 * Roda nos três formatos declarados no config. A mesma sequência em 1280, 810
 * e 412 pixels é o que revela layout que só quebra numa das larguras.
 */

import { expect, test, type Page } from '@playwright/test';
import {
  abrirSessaoComVaga, botaoReservar, cabecalho, CARTAO_APROVADO,
  CARTAO_RECUSADO, CLIENTE2, comprarIngresso, limparTurno, PORTARIA,
  sessaoDaPortaria, sessaoPath,
} from './apoio';
import { API } from '../playwright.config';

let passo = 0;

/** Grava o estado atual da tela, numerado na ordem em que aconteceu. */
async function capturar(page: Page, nome: string) {
  passo += 1;
  const projeto = test.info().project.name;
  const numero = String(passo).padStart(2, '0');
  /* Página inteira, menos quando ela é longa demais para valer a pena.
     A lista de ingressos acumula as compras de todas as execuções anteriores
     e chega a dezenas de milhares de pixels: o WebKit trava tentando compor a
     imagem, e o resultado seria ilegível de qualquer forma. */
  const altura = await page.evaluate(() => document.body.scrollHeight);

  await page.screenshot({
    path: `e2e/capturas/${projeto}/${numero}-${nome}.png`,
    fullPage: altura <= 6000,
    timeout: 60_000,
    animations: 'disabled',
  });
}

test.describe.configure({ mode: 'serial' });

test.describe('cliente', () => {
  test.use({ storageState: sessaoPath('cliente') });

  test('catálogo, busca e busca sem resultado', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 2 }).first())
      .toBeVisible({ timeout: 60_000 });
    await capturar(page, 'catalogo');

    await page.getByRole('searchbox').fill('duna');
    await expect(page.getByRole('heading', { level: 2 })).toHaveCount(1);
    await capturar(page, 'busca-com-resultado');

    await page.getByRole('searchbox').fill('zzzzzz');
    await expect(page.getByRole('heading', { level: 2 })).toHaveCount(0);
    await capturar(page, 'ERRO-busca-sem-resultado');
  });

  test('mapa de assentos e seleção', async ({ page, request }) => {
    await abrirSessaoComVaga(page, request);
    const livres = page.getByRole('button', { name: /Poltrona .+, livre/ });
    await expect(livres.first()).toBeVisible({ timeout: 30_000 });
    await capturar(page, 'mapa-de-assentos');

    await livres.nth(0).click();
    await livres.nth(0).click();
    await capturar(page, 'assentos-selecionados');
  });

  test('pagamento recusado e depois aprovado', async ({ page, request }) => {
    await abrirSessaoComVaga(page, request);
    const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
    await expect(livre).toBeVisible({ timeout: 30_000 });
    const poltrona = (await livre.getAttribute('aria-label'))!
      .match(/Poltrona (\S+?),/)![1];

    await livre.click();
    await botaoReservar(page).click();
    await expect(page).toHaveURL(/pagamento/, { timeout: 30_000 });
    await capturar(page, 'pagamento-formulario');

    await page.getByLabel(/n[úu]mero do cart/i).fill(CARTAO_RECUSADO);
    await page.getByLabel(/nome/i).fill('Bruno Tavares');
    await page.getByRole('button', { name: /pagar/i }).click();
    await expect(page.getByRole('heading', { name: /recusado/i }))
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'ERRO-pagamento-recusado');

    // A D13 diz que a poltrona segue reservada, então tentar de novo tem de valer.
    await page.getByRole('button', { name: /tentar outro cart/i }).click();
    await page.getByLabel(/n[úu]mero do cart/i).fill(CARTAO_APROVADO);
    await page.getByLabel(/nome/i).fill('Bruno Tavares');
    await page.getByRole('button', { name: /pagar/i }).click();
    await expect(page.getByRole('heading', { name: /compra confirmada/i }))
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'pagamento-aprovado');

    await page.getByRole('link', { name: /ver meus ingressos/i }).click();
    await expect(page.getByText(poltrona, { exact: false }).first())
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'meus-ingressos-com-qr');
  });

  test('poltrona levada por outra pessoa é recusada', async ({ page, request }) => {
    /* A garantia 1 aparecendo na tela, e não só no banco: entre abrir o mapa e
       confirmar, outra conta leva a mesma poltrona. */
    const showingId = await abrirSessaoComVaga(page, request);
    const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
    await expect(livre).toBeVisible({ timeout: 30_000 });
    const alvo = (await livre.getAttribute('aria-label'))!
      .match(/Poltrona (\S+?),/)![1];

    const h = await cabecalho(request, CLIENTE2);
    const assentos = await (await request.get(`${API}/showings/${showingId}/seats`)).json();
    const mesmo = assentos.find((a: { label: string }) => a.label === alvo);
    const pedido = await (await request.post(`${API}/showings/${showingId}/reservations`, {
      headers: h, data: { seat_ids: [mesmo.id] },
    })).json();
    await request.post(`${API}/orders/${pedido.id}/payment`, {
      headers: h,
      data: { card_number: CARTAO_APROVADO, holder_name: 'Carla Nogueira' },
    });

    await livre.click();
    await botaoReservar(page).click();
    await expect(page.getByText(/garantiu essa poltrona antes|ocupad/i).first())
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'ERRO-poltrona-disputada');
  });

  test('meus ingressos e compartilhamento', async ({ page }) => {
    await page.goto('/meus-ingressos');
    await expect(page.getByText(/c[óo]digo para digita/i).first())
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'meus-ingressos');

    const compartilhar = page.getByRole('button', { name: /compartilh|gerar link/i }).first();
    if (await compartilhar.count()) {
      await compartilhar.click();
      await page.waitForTimeout(600);
      await capturar(page, 'ingresso-com-link-de-compartilhamento');
    }
  });
});

test.describe('portaria', () => {
  test.use({ storageState: sessaoPath('portaria') });

  test('os desfechos da validação, um a um', async ({ page, request }) => {
    const sessao = await sessaoDaPortaria(request);
    const { codigo } = await comprarIngresso(request, sessao.showing_id);
    await limparTurno(request);

    await page.goto('/portaria');
    const escolha = page.getByRole('button', { name: new RegExp(sessao.event_title, 'i') }).first();
    await expect(escolha).toBeVisible({ timeout: 30_000 });
    await capturar(page, 'portaria-escolha-de-turno');

    await escolha.click();
    await expect(page.getByLabel(/digite o c[óo]digo/i)).toBeVisible({ timeout: 30_000 });
    await capturar(page, 'portaria-pronta-para-validar');

    const validar = async (valor: string) => {
      await page.getByLabel(/digite o c[óo]digo/i).fill(valor);
      await page.getByRole('button', { name: /^Validar$/ }).click();
      await expect(page.getByRole('alert')).toBeVisible({ timeout: 30_000 });
    };
    const seguir = () => page.getByRole('button', { name: /ler o pr[óo]ximo/i }).click();

    await validar(codigo);
    await capturar(page, 'portaria-VALIDO');
    await seguir();

    await validar(codigo);
    await capturar(page, 'ERRO-portaria-ja-utilizado');
    await seguir();

    await validar('codigo-que-nao-existe');
    await capturar(page, 'ERRO-portaria-invalido');
    await seguir();

    // Ingresso legítimo de outra exibição: encaminhamento, não fraude.
    const h = await cabecalho(request, PORTARIA);
    const turnos = await (await request.get(`${API}/gate/showings`, { headers: h })).json();
    const outra = turnos.find(
      (t: { showing_id: number }) => t.showing_id !== sessao.showing_id);
    if (outra) {
      const outro = await comprarIngresso(request, outra.showing_id);
      await validar(outro.codigo);
      await capturar(page, 'ERRO-portaria-lugar-errado');
    }
  });
});

test.describe('organizador', () => {
  test.use({ storageState: sessaoPath('organizador') });

  test('as três abas do painel', async ({ page }) => {
    await page.goto('/painel');
    await expect(page.getByRole('tab', { name: /eventos/i })).toBeVisible({ timeout: 30_000 });
    await capturar(page, 'painel-eventos-e-sessoes');

    await page.getByRole('tab', { name: /cinemas/i }).click();
    await expect(page.getByRole('button', { name: /adicionar cinema/i }))
      .toBeVisible({ timeout: 30_000 });
    await capturar(page, 'painel-cinemas-e-salas');

    await page.getByRole('tab', { name: /equipe/i }).click();
    await capturar(page, 'painel-equipe-e-cobertura');
  });

  test('busca de filme no TMDb', async ({ page }) => {
    /* Sem chave configurada, a API devolve 503 e a tela precisa dizer isso em
       vez de ficar em silêncio. Com chave, o mesmo passo mostra os resultados. */
    await page.goto('/painel');
    await page.getByRole('tab', { name: /eventos/i }).click();

    const busca = page.getByLabel(/t[íi]tulo do filme/i);
    await expect(busca).toBeVisible({ timeout: 30_000 });
    await busca.fill('matrix');
    await busca.press('Enter');
    await page.waitForTimeout(1500);
    await capturar(page, 'painel-busca-de-filme');
  });

  test('remoção recusada de cinema com sala', async ({ page }) => {
    await page.goto('/painel');
    await page.getByRole('tab', { name: /cinemas/i }).click();
    await expect(page.getByRole('button', { name: /adicionar cinema/i }))
      .toBeVisible({ timeout: 30_000 });

    const remover = page.getByRole('button', { name: /^Remover$/ }).first();
    if (await remover.count()) {
      await remover.click();
      await capturar(page, 'painel-confirmacao-de-remocao');

      const confirmar = page.getByRole('button', { name: /remover cinema|remover sala/i });
      if (await confirmar.count()) {
        await confirmar.click();
        await page.waitForTimeout(1200);
        await capturar(page, 'ERRO-remocao-recusada');
      }
    }
  });
});
