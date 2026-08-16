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
  gate_event_id: number | null;
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
  room_name: string;
  starts_at: string;
  audio: string;
}
