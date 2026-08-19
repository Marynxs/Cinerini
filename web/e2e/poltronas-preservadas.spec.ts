/* Regressão de um defeito real: escolher poltronas sem estar logado, ser
   mandado ao login, e voltar com o mapa em branco.

   O comentário no código já prometia preservar a seleção, e nada preservava.
   Este teste existe para que a promessa e o comportamento não voltem a
   divergir. */

import { expect, test } from '@playwright/test';
import { abrirSessaoComVaga, botaoReservar, CLIENTE, SENHA } from './apoio';

test('a seleção sobrevive ao login no meio da compra', async ({ page, request }) => {
  await abrirSessaoComVaga(page, request);

  const livre = page.getByRole('button', { name: /Poltrona .+, livre/ }).first();
  await expect(livre).toBeVisible({ timeout: 60_000 });

  const rotulo = await livre.getAttribute('aria-label');
  const poltrona = rotulo!.match(/Poltrona (\S+?),/)![1];
  await livre.click();

  // Deslogado, reservar manda para o login.
  await botaoReservar(page).click();
  await expect(page).toHaveURL(/\/entrar/, { timeout: 30_000 });

  await page.getByRole('button', { name: CLIENTE }).click();
  await page.getByLabel('Senha').fill(SENHA);
  await page.locator('form').getByRole('button', { name: 'Entrar' }).click();

  // De volta ao mapa, com a poltrona ainda escolhida.
  await expect(page).toHaveURL(/\/sessoes\/\d+/, { timeout: 30_000 });
  await expect(
    page.getByRole('button', { name: new RegExp(`Poltrona ${poltrona}.*selecionada`) })
  ).toHaveAttribute('aria-pressed', 'true', { timeout: 30_000 });
});
