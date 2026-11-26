// Corrida pelo mesmo assento: cada cliente tenta reservar a mesma poltrona,
// todos ao mesmo tempo. Exatamente um pode vencer.
//
//     k6 run -e BASE=http://api:8000 loadtest/corrida.js
//
// Bate direto na API, sem o Caddy: o que se mede é a arbitragem do índice
// único no banco (garantia 1), e não o TLS. Todas as tentativas saem de um IP
// só, então a API do teste sobe com REQUESTS_PER_MINUTE alto; com o teto de
// produção, 200 delas receberiam 429 antes de chegar ao banco.

import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const dados = JSON.parse(open('./corrida.json'));
const BASE = __ENV.BASE || 'http://localhost:8000';

const venceu = new Counter('reserva_vencida');
const perdeu = new Counter('reserva_recusada_409');
const outro = new Counter('reserva_outro_status');

export const options = {
  scenarios: {
    corrida: {
      // Cada cliente faz uma tentativa, e todos partem juntos.
      executor: 'per-vu-iterations',
      vus: dados.tokens.length,
      iterations: 1,
      maxDuration: '2m',
    },
  },
  thresholds: {
    reserva_vencida: ['count==1'],
    reserva_outro_status: ['count==0'],
  },
};

export default function () {
  const token = dados.tokens[__VU - 1];
  const r = http.post(
    `${BASE}/showings/${dados.showing_id}/reservations`,
    JSON.stringify({ seat_ids: [dados.seat_id] }),
    { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } },
  );

  if (r.status === 201) venceu.add(1);
  else if (r.status === 409) perdeu.add(1);
  else outro.add(1);

  check(r, { 'venceu ou recebeu 409': (res) => res.status === 201 || res.status === 409 });
}
