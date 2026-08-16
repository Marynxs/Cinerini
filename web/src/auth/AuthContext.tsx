import {
  createContext, useCallback, useContext, useEffect, useState,
  type ReactNode,
} from 'react';

import { aquecer, token as guardado } from '../api/client';
import { auth as api } from '../api/endpoints';
import type { User } from '../api/types';

interface Contexto {
  user: User | null;
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<User>;
  cadastrar: (nome: string, email: string, senha: string) => Promise<User>;
  sair: () => void;
}

const AuthContext = createContext<Contexto | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    // Acorda a API antes de qualquer clique: no plano gratuito ela hiberna,
    // e religar demora. Esse tempo passa enquanto a pessoa lê a tela.
    aquecer();

    if (!guardado.get()) {
      setCarregando(false);
      return;
    }

    // O token guardado pode estar expirado ou ser de um usuário removido.
    // Quem decide é a API, não o navegador.
    api.me()
      .then(setUser)
      .catch(() => guardado.clear())
      .finally(() => setCarregando(false));
  }, []);

  const entrar = useCallback(async (email: string, senha: string) => {
    const resposta = await api.login(email, senha);
    guardado.set(resposta.access_token);
    setUser(resposta.user);
    return resposta.user;
  }, []);

  const cadastrar = useCallback(
    async (nome: string, email: string, senha: string) => {
      const resposta = await api.register(nome, email, senha);
      guardado.set(resposta.access_token);
      setUser(resposta.user);
      return resposta.user;
    }, []);

  const sair = useCallback(() => {
    guardado.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, carregando, entrar, cadastrar, sair }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): Contexto {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error('useAuth precisa estar dentro de AuthProvider');
  return contexto;
}
