// Latência da leitura do catálogo, a rota que todo visitante chama primeiro.
//
//     k6 run -e BASE=https://54-157-43-152.sslip.io loadtest/leitura.js
//
// Carga moderada e só leitura: o alvo é o ambiente publicado, numa t4g.micro
// com créditos de CPU fixos, e o objetivo é medir, não derrubar. Quatro
// usuários a uma requisição por segundo ficam em 240 por minuto, abaixo do
// teto de 300 por IP: acima dele o teste mediria o 429, e não a leitura.

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '15s', target: 4 },
    { duration: '60s', target: 4 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
};

export default function () {
  const r = http.get(`${BASE}/events`);
  check(r, { 'status 200': (res) => res.status === 200 });
  sleep(1);
}
