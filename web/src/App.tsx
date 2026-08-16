/* Vitrine temporária da tela de escolha de poltrona.
   Sai quando as rotas e o cliente HTTP entrarem no lugar. */

import { SeatSelection, type Showing } from './screens/SeatSelection';
import type { Seat } from './components/SeatMap';

const LETRAS = 'ABCDEFGH';
const POR_FILEIRA = 12;

/* Ocupação irregular de propósito: distribuição uniforme esconderia como o
   mapa se comporta com poltronas soltas e blocos vendidos juntos. */
const OCUPADAS = new Set([
  'A5', 'A6', 'B3', 'B4', 'B5', 'C8', 'D1', 'D2', 'D11', 'D12',
  'E6', 'E7', 'F4', 'G9', 'G10', 'G11', 'H5',
]);

const ASSENTOS: Seat[] = LETRAS.split('').flatMap((letra, linha) =>
  Array.from({ length: POR_FILEIRA }, (_, i) => {
    const numero = i + 1;
    const label = `${letra}${numero}`;
    return {
      id: linha * POR_FILEIRA + numero,
      row_label: letra,
      number: numero,
      kind: linha === 0 && numero <= 2
        ? 'accessible' as const
        : 'standard' as const,
      label,
      taken: OCUPADAS.has(label),
    };
  }),
);

const SESSAO: Showing = {
  id: 1,
  starts_at: new Date(Date.now() + 86_400_000).toISOString(),
  audio: 'Dublado',
  price_cents: 3200,
  event_title: 'Duna: Parte Dois',
  poster_url: 'https://image.tmdb.org/t/p/w500/8LJJjLjAzAwXS40S5mx79PJ2jSs.jpg',
  runtime_minutes: 166,
  venue_name: 'Cine Belas Artes',
  room_name: 'Sala 1',
};

export default function App() {
  return (
    <SeatSelection
      showing={SESSAO}
      seats={ASSENTOS}
      onConfirm={(ids) => console.log('reservar', ids)}
    />
  );
}
