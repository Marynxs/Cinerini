/* As chamadas da API, uma função por rota.

   Reunidas aqui e não espalhadas pelas telas: quando um contrato muda, o
   ajuste fica num arquivo só, e o TypeScript aponta quem quebrou. */

import { request } from './client';
import type {
  EventOut, MyTicket, OrderOut, PaymentOut, SeatOut, SharedTicket,
  ShowingOut, TokenOut, User, Venue,
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

  eventos: () => request<EventOut[]>('/events', { publica: true }),

  evento: (id: number) =>
    request<EventOut>(`/events/${id}`, { publica: true }),

  sessoes: (eventId: number) =>
    request<ShowingOut[]>(`/events/${eventId}/showings`, { publica: true }),

  sessao: (id: number) =>
    request<ShowingOut>(`/showings/${id}`, { publica: true }),

  assentos: (showingId: number) =>
    request<SeatOut[]>(`/showings/${showingId}/seats`, { publica: true }),
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
