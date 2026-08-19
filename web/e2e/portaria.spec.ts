/* A portaria é a tela mais difícil de acertar e a mais fácil de quebrar sem
   ninguém notar: os desfechos precisam ser inconfundíveis a um metro de
   distância, com uma fila esperando.

   A câmera não entra aqui. Pedir vídeo ao navegador em teste exige um fluxo
   falso e testaria o jsQR, não a tela. A digitação é o caminho que a D20 criou
   justamente para quando a câmera falha, e exercita o mesmo veredito. */

import { expect, test } from '@playwright/test';
import {
  comprarIngresso, limparTurno, sessaoDaPortaria, sessaoPath,
} from './apoio';

test.use({ storageState: sessaoPath('portaria') });

test.describe('portaria', () => {
  test.beforeEach(async ({ request }) => {
    await limparTurno(request);
  });

  test('válido na primeira leitura, já utilizado na segunda', async ({ page, request }) => {
    const sessao = await sessaoDaPortaria(request);
    const { codigo, poltrona } = await comprarIngresso(request, sessao.showing_id);

    await page.goto('/portaria');

    // Escolher o turno é o primeiro gesto de quem chega para trabalhar (D24).
    await page.getByRole('button', { name: new RegExp(sessao.event_title, 'i') })
      .first().click();

    const campo = page.getByLabel(/digite o c[óo]digo/i);
    await expect(campo).toBeVisible({ timeout: 30_000 });

    await campo.fill(codigo);
    await page.getByRole('button', { name: /^Validar$/ }).click();

    const veredito = page.getByRole('alert');
    await expect(veredito).toContainText(/Válido/i, { timeout: 30_000 });
    await expect(veredito).toContainText(poltrona);

    // Segunda leitura do mesmo código.
    await page.getByRole('button', { name: /ler o pr[óo]ximo/i }).click();
    await campo.fill(codigo);
    await page.getByRole('button', { name: /^Validar$/ }).click();
    await expect(page.getByRole('alert')).toContainText(/utilizad/i, { timeout: 30_000 });
  });

  test('código inventado é inválido', async ({ page, request }) => {
    const sessao = await sessaoDaPortaria(request);

    await page.goto('/portaria');
    await page.getByRole('button', { name: new RegExp(sessao.event_title, 'i') })
      .first().click();

    await page.getByLabel(/digite o c[óo]digo/i).fill('codigo-que-nao-existe');
    await page.getByRole('button', { name: /^Validar$/ }).click();
    await expect(page.getByRole('alert')).toContainText(/inválid/i, { timeout: 30_000 });
  });

  test('o botão de seguir continua visível sob o ponteiro', async ({ page, request }) => {
    /* Regressão de um defeito de CSS: o hover invertia as cores usando
       `currentColor` no fundo e trocando o texto na mesma regra, e as duas
       caíam na mesma cor. O botão sumia no instante em que o dedo o procura. */
    const sessao = await sessaoDaPortaria(request);
    const { codigo } = await comprarIngresso(request, sessao.showing_id);

    await page.goto('/portaria');
    await page.getByRole('button', { name: new RegExp(sessao.event_title, 'i') })
      .first().click();
    await page.getByLabel(/digite o c[óo]digo/i).fill(codigo);
    await page.getByRole('button', { name: /^Validar$/ }).click();

    const seguir = page.getByRole('button', { name: /ler o pr[óo]ximo/i });
    await expect(seguir).toBeVisible({ timeout: 30_000 });

    await seguir.hover();
    const cores = await seguir.evaluate((el) => {
      const s = getComputedStyle(el);
      return { texto: s.color, fundo: s.backgroundColor };
    });
    expect(cores.texto, 'texto e fundo iguais: o botão some no hover')
      .not.toBe(cores.fundo);
  });
});
