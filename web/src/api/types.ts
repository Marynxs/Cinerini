/* Contratos da API.
   Espelham os schemas do back-end; qualquer divergência aparece aqui. */

export type Role = 'organizer' | 'customer' | 'gate';
export type TicketStatus = 'held' | 'valid' | 'used' | 'cancelled';
export type OrderStatus = 'pending' | 'paid' | 'refused' | 'cancelled';
export type SeatKind = 'standard' | 'accessible';

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  gate_showing_id: number | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Venue {
  id: number;
  name: string;
  city: string;
  /** Código do município no IBGE: é por ele que o catálogo agrupa (D23). */
  city_ibge_id: number;
  state: string;
  address: string;
}

export interface Room {
  id: number;
  venue_id: number;
  name: string;
  rows: number;
  seats_per_row: number;
  capacity: number;
}

export interface EventOut {
  id: number;
  tmdb_id: number | null;
  title: string;
  synopsis: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  runtime_minutes: number | null;
  status: 'draft' | 'published';
}

export interface ShowingOut {
  id: number;
  event_id: number;
  room_id: number;
  starts_at: string;
  audio: string;
  price_cents: number;

  venue_name: string;
  venue_city: string;
  venue_address: string;
  room_name: string;
  seats_available: number;

  seats_total: number;
  cancelled_at: string | null;
  cancellation_reason: string | null;

  /** Repetido do evento para a tela de assentos não precisar buscá-lo. */
  event_title: string;
  poster_url: string | null;
  runtime_minutes: number | null;
}

export interface TmdbSearchResult {
  tmdb_id: number;
  title: string;
  year: string | null;
  synopsis: string | null;
  poster_url: string | null;
}

/** Filme em cartaz com suas sessões, como o catálogo devolve. */
export interface CatalogEvent {
  id: number;
  title: string;
  synopsis: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  runtime_minutes: number | null;
  showings: ShowingOut[];
}

export interface SeatOut {
  id: number;
  row_label: string;
  number: number;
  kind: SeatKind;
  label: string;
  taken: boolean;
}

export interface TicketOut {
  id: number;
  jti: string;
  status: TicketStatus;
  seat_id: number;
  seat_label: string;
  row_label: string;
  number: number;
}

export interface OrderOut {
  id: number;
  showing_id: number;
  status: OrderStatus;
  total_cents: number;
  held_until: string | null;
  tickets: TicketOut[];
}

export interface PaymentOut {
  approved: boolean;
  reason: string | null;
  order: OrderOut;
}

export interface MyTicket {
  id: number;
  jti: string;
  status: TicketStatus;
  seat_label: string;
  qr_token: string;
  event_title: string;
  poster_url: string | null;
  venue_name: string;
  venue_address: string;
  venue_city: string;
  room_name: string;
  starts_at: string;
  audio: string;
  price_cents: number;
  showing_cancelled: boolean;
  cancellation_reason: string | null;
}

export interface SharedTicket {
  status: TicketStatus;
  seat_label: string;
  qr_token: string;
  event_title: string;
  poster_url: string | null;
  venue_name: string;
  venue_address: string;
  venue_city: string;
  room_name: string;
  starts_at: string;
  audio: string;
}

export type GateResult =
  | 'valid' | 'invalid' | 'already_used'
  | 'wrong_event' | 'wrong_showing' | 'cancelled';

/** Uma exibição em uma linha: o que a portaria mostra e confere. */
export interface ShowingBrief {
  /** Presente na lista de turnos, ausente no veredito de validação. */
  showing_id: number | null;
  event_id: number;
  event_title: string;
  starts_at: string;
  venue_name: string;
  venue_city: string;
  room_name: string;
}

export interface Gate {
  id: number;
  name: string;
  email: string;
  /** O cinema onde a conta trabalha. Definido pelo organizador. */
  venue_id: number | null;
  venue_name: string | null;
  /** A sessão do turno. Escolhida pelo próprio funcionário. */
  showing_id: number | null;
  showing: ShowingBrief | null;
}

export interface Validation {
  result: GateResult;
  seat_label: string | null;
  customer_name: string | null;
  showing: ShowingBrief | null;
  used_at: string | null;
}

/** Cidade com cinema, para o filtro do catálogo.

    Traz a UF porque nome de cidade se repete entre estados. */
export interface City {
  id: number;
  nome: string;
  uf: string;
}

export interface Uf {
  sigla: string;
  nome: string;
}

export interface Municipio {
  id: number;
  nome: string;
}

/** Uma sessão e quem está na porta dela. Lista vazia é o dado que importa. */
export interface CoverageStaff {
  name: string;
  // Organizador cobrindo a porta conta como alguém, mas não é funcionário
  // alocado, porque a tabela da equipe não o edita (D33).
  organizer: boolean;
}

export interface Coverage {
  showing: ShowingBrief;
  staff: CoverageStaff[];
}
