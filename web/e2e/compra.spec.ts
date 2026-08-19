/* O percurso que o desafio existe para exercitar: escolher, pagar, receber. */

import { expect, test } from '@playwright/test';
import {
  abrirSessaoComVaga, botaoReservar, CARTAO_APROVADO, CARTAO_RECUSADO, sessaoPath,
} from './apoio';

// Sessão gravada pelo projeto de preparo: logar aqui gastaria tentativas do
// limitador sem testar nada que a tela de login já não cubra.
test.use({ storageState: sessaoPath('cliente') });

test.describe('compra', () => {
  test('escolhe poltrona, paga e recebe o ingresso com QR', async ({ page, request }) => {
    await abrirSessaoComVaga(page, request);

    const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
    await expect(livre).toBeVisible({ timeout: 30_000 });

    const rotulo = await livre.getAttribute('aria-label');
    const poltrona = rotulo!.match(/Poltrona (\S+?),/)![1];
    await livre.click();

    // A seleção precisa aparecer no estado do próprio botão, e não só na cor:
    // é o que a leitura em voz alta anuncia.
    await expect(page.getByRole('button', { name: new RegExp(`Poltrona ${poltrona}.*selecionada`) }))
      .toHaveAttribute('aria-pressed', 'true');

    await botaoReservar(page).click();

    await expect(page).toHaveURL(/\/pedidos\/\d+\/pagamento/, { timeout: 30_000 });
    await page.getByLabel(/n[úu]mero do cart/i).fill(CARTAO_APROVADO);
    await page.getByLabel(/nome/i).fill('Bruno Tavares');
    await page.getByRole('button', { name: /pagar/i }).click();

    await expect(page.getByRole('heading', { name: /compra confirmada/i }))
      .toBeVisible({ timeout: 30_000 });

    await page.getByRole('link', { name: /ver meus ingressos/i }).click();
    await expect(page).toHaveURL(/meus-ingressos/, { timeout: 30_000 });
    await expect(page.getByText(poltrona, { exact: false }).first()).toBeVisible();

    // O qrcode.react desenha um <svg>. Vale conferir também o código para
    // digitação, que é o caminho alternativo da D20 e o que permite demonstrar
    // a portaria num computador só.
    await expect(page.locator('svg').first()).toBeVisible();
    await expect(page.getByText(/c[óo]digo para digita/i).first()).toBeVisible();
  });

  test('cartão terminado em zero é recusado e a compra continua possível', async ({ page, request }) => {
    await abrirSessaoComVaga(page, request);

    const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
    await expect(livre).toBeVisible({ timeout: 30_000 });
    await livre.click();
    await botaoReservar(page).click();

    await expect(page).toHaveURL(/pagamento/, { timeout: 30_000 });
    await page.getByLabel(/n[úu]mero do cart/i).fill(CARTAO_RECUSADO);
    await page.getByLabel(/nome/i).fill('Bruno Tavares');
    await page.getByRole('button', { name: /pagar/i }).click();

    // Recusa explícita, e não um erro genérico.
    await expect(page.getByRole('heading', { name: /pagamento recusado/i }))
      .toBeVisible({ timeout: 30_000 });

    /* A D13 diz que a poltrona continua reservada e o pedido segue pagável:
       um dígito errado não pode custar a escolha inteira. A tela precisa
       dizer isso, e dizia o contrário — "as poltronas voltaram para o mapa" —
       mandando o cliente reescolher o que ainda era dele. */
    await expect(page.getByText(/continuam reservadas/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /tentar outro cart/i }))
      .toBeEnabled();
  });
});
