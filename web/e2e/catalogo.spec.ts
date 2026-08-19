/* O catálogo é a primeira tela que o avaliador abre. */

import { expect, test } from '@playwright/test';

test.describe('catálogo', () => {
  test('lista os filmes em cartaz com data, local e preço', async ({ page }) => {
    await page.goto('/');

    // Espera pelo conteúdo, e não por um tempo fixo: a API do plano gratuito
    // hiberna, e um `waitForTimeout` ora sobra ora falta.
    const cartoes = page.getByRole('heading', { level: 2 });
    await expect(cartoes.first()).toBeVisible({ timeout: 60_000 });
    expect(await cartoes.count()).toBeGreaterThan(0);

    // Preço em reais, nunca centavos crus na tela.
    await expect(page.getByText(/R\$\s?\d/).first()).toBeVisible();
  });

  test('a busca filtra por título', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 2 }).first())
      .toBeVisible({ timeout: 60_000 });

    const antes = await page.getByRole('heading', { level: 2 }).count();
    await page.getByRole('searchbox').fill('duna');

    const depois = page.getByRole('heading', { level: 2 });
    await expect(depois).toHaveCount(1);
    expect(antes).toBeGreaterThan(1);
    await expect(depois.first()).toContainText(/duna/i);
  });

  test('busca sem resultado explica em vez de mostrar tela vazia', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 2 }).first())
      .toBeVisible({ timeout: 60_000 });

    await page.getByRole('searchbox').fill('zzzzzzzz');
    await expect(page.getByRole('heading', { level: 2 })).toHaveCount(0);
    await expect(page.getByText(/nada|nenhum/i).first()).toBeVisible();
  });
});
