/* As chamadas da API, uma função por rota.

   Reunidas aqui e não espalhadas pelas telas: quando um contrato muda, o
   ajuste fica num arquivo só, e o TypeScript aponta quem quebrou. */

import { request } from './client';
import type {
  CatalogEvent, City, Coverage, EventOut, Gate, Municipio, MyTicket, OrderOut,
  PaymentOut, Room, SeatOut, SharedTicket, ShowingBrief, ShowingOut,
  TmdbSearchResult, TokenOut, Uf, User, Validation, Venue,
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
  cidades: () => request<City[]>('/venues/cities', { publica: true }),

  // `cidade` é o código do município no IBGE, não o nome: nome de cidade
  // se repete entre estados (D23).
  cinemas: (cidade?: number) =>
    request<Venue[]>(cidade ? `/venues?city=${cidade}` : '/venues',
                     { publica: true }),

  eventos: (cidade?: number) =>
    request<CatalogEvent[]>(cidade ? `/events?city=${cidade}` : '/events',
                            { publica: true }),

  ufs: () => request<Uf[]>('/venues/ufs', { publica: true }),

  municipios: (uf: string) =>
    request<Municipio[]>(`/venues/ufs/${uf}/municipios`, { publica: true }),

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
    name: string; state: string; city_ibge_id: number; address: string;
  }) => request<Venue>('/venues', { method: 'POST', body: dados }),

  editarCinema: (venueId: number, dados: Partial<{
    name: string; state: string; city_ibge_id: number; address: string;
  }>) => request<Venue>(`/venues/${venueId}`, { method: 'PATCH', body: dados }),

  removerCinema: (venueId: number) =>
    request<void>(`/venues/${venueId}`, { method: 'DELETE' }),

  editarSala: (venueId: number, roomId: number, dados: Partial<{
    name: string; rows: number; seats_per_row: number;
  }>) => request<Room>(`/venues/${venueId}/rooms/${roomId}`, {
    method: 'PATCH', body: dados,
  }),

  removerSala: (venueId: number, roomId: number) =>
    request<void>(`/venues/${venueId}/rooms/${roomId}`, { method: 'DELETE' }),

  organizadores: () => request<User[]>('/auth/organizers'),

  promover: (email: string) =>
    request<User>('/auth/organizers', { method: 'POST', body: { email } }),

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

export const portaria = {
  vinculo: () => request<Gate>('/gate/me'),

  validar: (code: string) =>
    request<Validation>('/gate/validations', { method: 'POST', body: { code } }),

  // As sessões que esta conta pode atender, e a escolha do turno. Quem
  // escolhe é quem trabalha, não o organizador (D24).
  turnos: () => request<ShowingBrief[]>('/gate/showings'),

  escolherTurno: (showingId: number | null) =>
    request<Gate>('/gate/shift', {
      method: 'PUT', body: { showing_id: showingId },
    }),

  // Cadastro é do organizador, nunca da própria portaria.
  listar: () => request<Gate[]>('/gates'),

  // Sessões começando em breve e quem as atende. Vira a pergunta do avesso:
  // não "o que o João atende", e sim "esta sessão tem alguém" (D26).
  cobertura: () => request<Coverage[]>('/gates/coverage'),

  criar: (venueId: number, dados: {
    name: string; email: string; password: string;
  }) => request<Gate>(`/venues/${venueId}/gates`, {
    method: 'POST', body: dados,
  }),

  // Nome e cinema, nunca a senha: trocá-la pelo painel obrigaria a entregar
  // a nova por algum canal (D22).
  editar: (gateId: number, dados: Partial<{
    name: string; venue_id: number | null;
  }>) => request<Gate>(`/gates/${gateId}`, { method: 'PATCH', body: dados }),

  remover: (gateId: number) =>
    request<void>(`/gates/${gateId}`, { method: 'DELETE' }),
};
