import { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthProvider } from './auth/AuthContext';
import { Carregando, Layout } from './components/Layout';
import { Catalog } from './screens/Catalog';
import { Login } from './screens/Login';
import { MyTickets } from './screens/MyTickets';
import { Organizer } from './screens/Organizer';
import { Payment } from './screens/Payment';
import { SharedTicket } from './screens/SharedTicket';
import { SeatSelectionPage } from './screens/SeatSelectionPage';

/* A portaria carrega o decodificador de QR, que sozinho pesa mais que o
   resto do sistema junto. Separá-la evita que todo cliente comprando
   ingresso baixe um leitor de câmera que nunca vai abrir. */
const Gate = lazy(() =>
  import('./screens/Gate').then((m) => ({ default: m.Gate })));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Catalog />} />
          <Route path="/entrar" element={<Login />} />
          <Route path="/sessoes/:id" element={<SeatSelectionPage />} />
          <Route path="/pedidos/:id/pagamento" element={<Payment />} />
          <Route path="/meus-ingressos" element={<MyTickets />} />
          <Route path="/painel" element={<Organizer />} />
          <Route
            path="/portaria"
            element={(
              <Suspense
                fallback={<Layout><Carregando texto="Abrindo a portaria" /></Layout>}
              >
                <Gate />
              </Suspense>
            )}
          />
          <Route path="/ingresso/:token" element={<SharedTicket />} />

          {/* Endereço desconhecido volta ao catálogo em vez de abrir uma tela
              de erro: não há aqui nada que só exista numa URL específica. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
