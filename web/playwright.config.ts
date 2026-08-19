/* Testes de ponta a ponta do front.
 *
 * Rodam contra a pilha do Compose, e não contra dublês: `docker compose up -d`
 * levanta banco, API e front já semeados, então o teste exercita o mesmo
 * artefato que o avaliador abre. É a mesma regra que vale para a API, onde a
 * verificação é sempre por HTTP contra o servidor de verdade.
 */

import { defineConfig, devices } from '@playwright/test';

export const API = process.env.E2E_API ?? 'http://localhost:8000';
export const APP = process.env.E2E_APP ?? 'http://localhost:5173';

export default defineConfig({
  testDir: './e2e',

  // Um trabalhador só, de propósito: os testes compram poltronas de verdade
  // num banco compartilhado, e dois em paralelo disputariam o mesmo assento.
  // A recusa por disputa é comportamento correto do sistema, e faria o teste
  // falhar por um motivo que não é o dele.
  workers: 1,
  fullyParallel: false,

  // Repetição só na integração contínua. Na máquina de quem desenvolve, teste
  // instável precisa aparecer como instável.
  retries: process.env.CI ? 2 : 0,
  forbidOnly: !!process.env.CI,

  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: APP,

    // Rastro só do que falhou, e na primeira repetição: guardar tudo enche o
    // disco e ninguém abre o rastro do que passou.
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
  },

  projects: [
    // Autentica uma vez e grava a sessão. Sem isto, cada teste faria login e
    // a suíte estouraria o limitador de tentativas da própria API (D8).
    { name: 'preparo', testMatch: /auth\.setup\.ts/ },

    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['preparo'],
    },

    // O tablet é a largura que costuma escapar: larga demais para o layout de
    // celular, estreita demais para o de computador. É onde a barra fixa e o
    // resumo lateral podem aparecer ao mesmo tempo, ou sumir os dois.
    {
      name: 'tablet',
      use: { ...devices['iPad (gen 7)'] },
      dependencies: ['preparo'],
    },

    // O celular não é enfeite: a portaria é operada no aparelho de quem está
    // na porta, e o mapa de assentos foi o que mais quebrou em tela estreita.
    {
      name: 'celular',
      use: { ...devices['Pixel 7'] },
      dependencies: ['preparo'],
    },
  ],
});
