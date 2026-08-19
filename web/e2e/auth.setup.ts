/* Autentica uma vez por papel e guarda a sessão em disco.
 *
 * Existe por um motivo concreto: o sistema tem limitador de tentativas (D8),
 * oito por conta a cada quinze minutos. Uma suíte que faz login em cada teste
 * estoura esse limite e passa a falhar com 429 — e o pior é que falha nos
 * testes seguintes, não no que gastou as tentativas.
 *
 * Reaproveitar a sessão também deixa a suíte muito mais rápida: o login deixa
 * de ser repetido em todo teste que só precisa de alguém logado.
 *
 * A tela de login continua coberta: o teste da seleção de poltronas percorre
 * o formulário de verdade, e é lá que ele é exercitado.
 */

import { test as setup, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { API } from '../playwright.config';
import { APP } from '../playwright.config';
import { CLIENTE, CLIENTE2, ORGANIZADOR, PORTARIA, SENHA, sessaoPath } from './apoio';

const PAPEIS = [
  ['cliente', CLIENTE],
  ['cliente2', CLIENTE2],
  ['organizador', ORGANIZADOR],
  ['portaria', PORTARIA],
] as const;

for (const [nome, email] of PAPEIS) {
  setup(`sessão de ${nome}`, async ({ request }) => {
    const r = await request.post(`${API}/auth/login`, {
      data: { email, password: SENHA },
    });
    expect(r.ok(), `login de ${email} falhou: ${r.status()}`).toBeTruthy();
    const { access_token } = await r.json();

    // O app guarda o token em localStorage, então a sessão gravada é isso.
    const estado = {
      cookies: [],
      origins: [{
        origin: APP,
        localStorage: [{ name: 'cinerini.token', value: access_token }],
      }],
    };

    const destino = sessaoPath(nome);
    fs.mkdirSync(path.dirname(destino), { recursive: true });
    fs.writeFileSync(destino, JSON.stringify(estado, null, 2));
  });
}
