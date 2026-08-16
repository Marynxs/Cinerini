import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthProvider } from './auth/AuthContext';
import { Catalog } from './screens/Catalog';
import { Login } from './screens/Login';
import { MyTickets } from './screens/MyTickets';
import { Payment } from './screens/Payment';
import { SharedTicket } from './screens/SharedTicket';
import { SeatSelectionPage } from './screens/SeatSelectionPage';

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
          <Route path="/ingresso/:token" element={<SharedTicket />} />

          {/* Endereço desconhecido volta ao catálogo em vez de abrir uma tela
              de erro: não há aqui nada que só exista numa URL específica. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
