/* As chamadas da API, uma função por rota.

   Reunidas aqui e não espalhadas pelas telas: quando um contrato muda, o
   ajuste fica num arquivo só, e o TypeScript aponta quem quebrou. */

import { request } from './client';
import type {
  CatalogEvent, EventOut, MyTicket, OrderOut, PaymentOut, Room, SeatOut,
  SharedTicket, ShowingOut, TmdbSearchResult, TokenOut, User, Venue,
} from './types';

export const auth = {
  login: (email: string, password: string) =>
    request<TokenOut>('/auth/login', {
      method: 'POST', body: { email, password }, publica: true,
    }),

  register: (name: string, email: string, password: string) =>
    request<TokenOut>('/auth/register', {
      method: 'POST', body: { name, email, password }, publica: true,
    }),

  me: () => request<User>('/auth/me'),
};

export const catalogo = {
  cidades: () => request<string[]>('/venues/cities', { publica: true }),

  cinemas: (cidade?: string) =>
    request<Venue[]>(
      cidade ? `/venues?city=${encodeURIComponent(cidade)}` : '/venues',
      { publica: true },
    ),

  eventos: (cidade?: string) =>
    request<CatalogEvent[]>(
      cidade ? `/events?city=${encodeURIComponent(cidade)}` : '/events',
      { publica: true },
    ),

  evento: (id: number) =>
    request<EventOut>(`/events/${id}`, { publica: true }),

  sessoes: (eventId: number) =>
    request<ShowingOut[]>(`/events/${eventId}/showings`, { publica: true }),

  sessao: (id: number) =>
    request<ShowingOut>(`/showings/${id}`, { publica: true }),

  assentos: (showingId: number) =>
    request<SeatOut[]>(`/showings/${showingId}/seats`, { publica: true }),

  salas: (venueId: number) =>
    request<Room[]>(`/venues/${venueId}/rooms`, { publica: true }),
};

export const organizador = {
  meusEventos: () => request<EventOut[]>('/events/mine'),

  buscarFilme: (termo: string) =>
    request<TmdbSearchResult[]>(
      `/catalog/search?q=${encodeURIComponent(termo)}`),

  criarEvento: (tmdbId: number) =>
    request<EventOut>('/events', { method: 'POST', body: { tmdb_id: tmdbId } }),

  publicar: (eventId: number) =>
    request<EventOut>(`/events/${eventId}/publish`, { method: 'POST' }),

  despublicar: (eventId: number) =>
    request<EventOut>(`/events/${eventId}/unpublish`, { method: 'POST' }),

  criarSessao: (eventId: number, dados: {
    room_id: number; starts_at: string; price_cents: number; audio: string;
  }) =>
    request<ShowingOut>(`/events/${eventId}/showings`, {
      method: 'POST', body: dados,
    }),

  cancelarSessao: (showingId: number, reason: string) =>
    request<ShowingOut>(`/showings/${showingId}/cancel`, {
      method: 'POST', body: { reason },
    }),

  criarCinema: (dados: {
    name: string; city: string; state: string; address: string;
  }) => request<Venue>('/venues', { method: 'POST', body: dados }),

  criarSala: (venueId: number, dados: {
    name: string; rows: number; seats_per_row: number;
  }) => request<Room>(`/venues/${venueId}/rooms`, {
    method: 'POST', body: dados,
  }),
};

export const compra = {
  reservar: (showingId: number, seatIds: number[]) =>
    request<OrderOut>(`/showings/${showingId}/reservations`, {
      method: 'POST', body: { seat_ids: seatIds },
    }),

  pagar: (orderId: number, cardNumber: string, holderName: string) =>
    request<PaymentOut>(`/orders/${orderId}/payment`, {
      method: 'POST',
      body: { card_number: cardNumber, holder_name: holderName },
    }),

  meusPedidos: () => request<OrderOut[]>('/me/orders'),

  meusIngressos: () => request<MyTicket[]>('/me/tickets'),

  cancelarIngresso: (ticketId: number) =>
    request<MyTicket[]>(`/tickets/${ticketId}/cancel`, { method: 'POST' }),
};

export const compartilhamento = {
  criar: (ticketId: number) =>
    request<{ token: string; revoked: boolean; created_at: string }>(
      `/tickets/${ticketId}/share`, { method: 'POST' },
    ),

  revogar: (token: string) =>
    request<void>(`/share/${token}`, { method: 'DELETE' }),

  abrir: (token: string) =>
    request<SharedTicket>(`/share/${token}`, { publica: true }),
};
