/* Comportamento que muda com o tamanho da tela.
 *
 * Existe porque foi onde o projeto mais quebrou: mapa vazando pela direita,
 * rótulo da trilha cortado à esquerda, e fileiras de cima inalcançáveis numa
 * sala alta. Nenhum desses aparece num teste que só roda em 1280px.
 */

import { expect, test, type Page } from '@playwright/test';
import {
  abrirSessaoComVaga, botaoReservar, entrarNaPortaria, sessaoPath,
} from './apoio';

/** A página inteira nunca deve rolar na horizontal.
 *
 *  O mapa tem rolagem própria por dentro, e isso é decisão de projeto. O que
 *  não pode é a página empurrar conteúdo para fora da tela: aí não há gesto
 *  que alcance o que ficou de fora. */
async function paginaNaoVazaNaHorizontal(page: Page) {
  const vaza = await page.evaluate(() => {
    const d = document.documentElement;
    // Um pixel de folga para arredondamento de layout.
    return d.scrollWidth - d.clientWidth > 1;
  });
  expect(vaza, 'a página rola na horizontal').toBe(false);
}

test.use({ storageState: sessaoPath('cliente') });

test.describe('celular', () => {
  // `isMobile` vem do próprio descritor do aparelho, então o recorte segue
  // o dispositivo e não o nome que dei ao projeto.
  test.skip(({ isMobile }) => !isMobile, 'só faz sentido em tela estreita');

  test('nenhuma tela do fluxo vaza pela lateral', async ({ page, request }) => {

    await page.goto('/');
    await expect(page.getByRole('heading', { level: 2 }).first())
      .toBeVisible({ timeout: 60_000 });
    await paginaNaoVazaNaHorizontal(page);

    await abrirSessaoComVaga(page, request);
    await expect(page.getByRole('button', { name: /Poltrona .+, livre/ }).first())
      .toBeVisible({ timeout: 30_000 });
    await paginaNaoVazaNaHorizontal(page);

    await page.goto('/meus-ingressos');
    await paginaNaoVazaNaHorizontal(page);

    await page.goto('/portaria');
    await paginaNaoVazaNaHorizontal(page);
  });

  test('a barra fixa aparece ao escolher e some quando o resumo entra', async ({ page, request, viewport }) => {
    /* Só no telefone. No tablet a tela é alta o bastante para o resumo já
       estar visível ao abrir, e aí a barra nasce cedendo o lugar a ele: o
       botão vem desabilitado de propósito, para não haver duas ações iguais.
       É o mesmo comportamento, num ponto diferente da mesma regra. */
    test.skip(!viewport || viewport.width >= 600, 'premissa é de tela estreita');

    await abrirSessaoComVaga(page, request);

    const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
    await expect(livre).toBeVisible({ timeout: 30_000 });

    const barra = page.locator('.barra-fixa');
    await livre.click();

    // Com poltrona escolhida, a ação precisa estar ao alcance do polegar sem
    // rolar até o fim da página.
    await expect(barra).toBeVisible();
    await expect(barra).toContainText(/1 poltrona/);
    // "Atualizar" quando já existe reserva aberta nesta sessão (D14): o mesmo
    // botão troca de rótulo, e o teste não pode depender de qual execução veio
    // antes.
    await expect(barra.getByRole('button', { name: /^(Reservar|Atualizar)$/ }))
      .toBeEnabled();

    // Ao chegar no resumo, a barra sai: duas ações idênticas na mesma tela
    // fazem a pessoa parar para decidir qual apertar.
    await botaoReservar(page).scrollIntoViewIfNeeded();
    await expect(barra).toHaveClass(/barra-fixa--oculta/);
  });

  test('a ficha da sessão ocupa a largura toda quando não há pôster', async ({ page, request }) => {
    /* O `<img>` do pôster é renderizado só quando existe. Sem ele, o bloco de
       texto virava o primeiro filho do grid e caía na coluna estreita
       reservada à imagem: a ficha inteira ficava com 84px numa tela de 412, e
       cada valor quebrava em duas linhas. Acontece em todo filme sem pôster,
       que é o cenário semeado sem chave do TMDb. */
    await abrirSessaoComVaga(page, request);
    await expect(page.getByRole('button', { name: /Poltrona .+, livre/ }).first())
      .toBeVisible({ timeout: 60_000 });

    const medida = await page.evaluate(() => {
      const bloco = document.querySelector('.ficha-dados') as HTMLElement;
      return {
        bloco: bloco.getBoundingClientRect().width,
        janela: window.innerWidth,
      };
    });

    // Sem exigir largura exata: o que não pode é a ficha ficar presa na
    // coluna do pôster, que é uma fração pequena da tela.
    expect(medida.bloco).toBeGreaterThan(medida.janela * 0.5);
  });

  test('todas as fileiras do mapa continuam alcançáveis', async ({ page, request }) => {
    /* O invólucro de rolagem nasceu com `overflow-y: hidden` e cortava as
       fileiras de cima numa sala alta, sem gesto que chegasse nelas. */
    await abrirSessaoComVaga(page, request);
    const assentos = page.getByRole('button', { name: /^Poltrona / });
    await expect(assentos.first()).toBeVisible({ timeout: 60_000 });

    const total = await assentos.count();
    const ultimo = assentos.nth(total - 1);

    await ultimo.scrollIntoViewIfNeeded();
    await expect(ultimo).toBeInViewport();
  });

  test.describe('portaria no celular', () => {
    test.use({ storageState: sessaoPath('portaria') });

  test('o veredito da portaria é legível a um metro', async ({ page, request }) => {
    await entrarNaPortaria(page, request);

    await page.getByLabel(/digite o c[óo]digo/i).fill('codigo-que-nao-existe');
    await page.getByRole('button', { name: /^Validar$/ }).click();

    const veredito = page.getByRole('alert');
    await expect(veredito).toBeVisible({ timeout: 30_000 });

    // A palavra do desfecho é o que se lê de longe, com fila esperando.
    const tamanho = await veredito.locator('.veredito-palavra').evaluate(
      (el) => parseFloat(getComputedStyle(el).fontSize));
    expect(tamanho, 'a palavra do veredito encolheu demais no celular')
      .toBeGreaterThanOrEqual(24);

    await paginaNaoVazaNaHorizontal(page);
  });
  });
});

test.describe('computador', () => {
  test.skip(({ isMobile }) => isMobile, 'só faz sentido em tela larga');

  test('o rótulo da trilha fica sob o ícone', async ({ page, request }) => {
    /* No celular o rótulo vai ao lado do disco, para caber. No computador ele
       volta para baixo, que é onde a trilha foi desenhada. */
    await abrirSessaoComVaga(page, request);

    const disco = page.locator('.trilha-disco').first();
    const rotulo = page.locator('.trilha-rotulo').first();
    await expect(rotulo).toBeVisible({ timeout: 30_000 });

    const cx = (await disco.boundingBox())!;
    const cr = (await rotulo.boundingBox())!;
    expect(cr.y, 'o rótulo não está abaixo do disco').toBeGreaterThan(cx.y);
  });
});
