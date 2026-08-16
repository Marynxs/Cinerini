import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { Layout, Voltar } from '../components/Layout';
import './Login.css';

/* Contas do seed, para quem avalia não precisar digitar. Só aparecem contra
   a API local — em produção seriam um convite a testar credenciais. */
const CONTAS_SEMEADAS = [
  { papel: 'Organizador', email: 'organizador@cinerini.com.br' },
  { papel: 'Cliente', email: 'cliente1@cinerini.com.br' },
  { papel: 'Cliente', email: 'cliente2@cinerini.com.br' },
  { papel: 'Portaria', email: 'portaria@cinerini.com.br' },
];

const SENHA_SEMEADA = 'cinerini123';

const ehLocal = (import.meta.env.VITE_API_URL ?? '').includes('localhost');

export function Login() {
  const { entrar, cadastrar } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();

  const [aba, setAba] = useState<'entrar' | 'cadastrar'>('entrar');
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Para onde voltar depois de entrar. Quem clicou numa sessão e foi parar
  // aqui espera cair de volta na sessão, não no catálogo.
  const destino = (local.state as { de?: string } | null)?.de ?? '/';

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    try {
      const usuario = aba === 'entrar'
        ? await entrar(email, senha)
        : await cadastrar(nome, email, senha);

      // Portaria e organizador não têm tela ainda; por ora todos voltam ao
      // ponto de origem.
      navegar(usuario.role === 'customer' ? destino : '/', { replace: true });
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  function preencher(emailConta: string) {
    setAba('entrar');
    setEmail(emailConta);
    setSenha(SENHA_SEMEADA);
    setErro(null);
  }

  return (
    <Layout>
      <Voltar para="/" texto="Catálogo" />

      <div className="entrada">
        <div className="entrada-abas">
          <button
            type="button"
            className={`entrada-aba${aba === 'entrar' ? ' entrada-aba--ativa' : ''}`}
            onClick={() => { setAba('entrar'); setErro(null); }}
          >
            Entrar
          </button>
          <button
            type="button"
            className={`entrada-aba${aba === 'cadastrar' ? ' entrada-aba--ativa' : ''}`}
            onClick={() => { setAba('cadastrar'); setErro(null); }}
          >
            Criar conta
          </button>
        </div>

        <div className="entrada-corpo">
          <h1 className="entrada-titulo">
            {aba === 'entrar' ? 'Acesse sua conta' : 'Crie sua conta'}
          </h1>

          {erro && (
            <p className="erro-form" role="alert">
              <span className="erro-form-marca" aria-hidden="true">!</span>
              {erro}
            </p>
          )}

          <form onSubmit={enviar}>
            {aba === 'cadastrar' && (
              <label className="campo">
                <span className="campo-rotulo">Nome</span>
                <input
                  className="campo-entrada"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  required
                  minLength={2}
                  autoComplete="name"
                />
              </label>
            )}

            <label className="campo">
              <span className="campo-rotulo">E-mail</span>
              <input
                className="campo-entrada"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </label>

            <label className="campo">
              <span className="campo-rotulo">Senha</span>
              <input
                className="campo-entrada"
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                minLength={aba === 'cadastrar' ? 8 : undefined}
                autoComplete={aba === 'entrar' ? 'current-password' : 'new-password'}
              />
              {aba === 'cadastrar' && (
                <span className="campo-ajuda">Mínimo de 8 caracteres.</span>
              )}
            </label>

            <button type="submit" className="acao" disabled={enviando}>
              {enviando
                ? 'Enviando…'
                : aba === 'entrar' ? 'Entrar' : 'Criar conta'}
            </button>
          </form>

          {ehLocal && (
            <div className="contas">
              <p className="contas-titulo">Contas de teste</p>
              {CONTAS_SEMEADAS.map((conta) => (
                <button
                  key={conta.email}
                  type="button"
                  className="conta"
                  onClick={() => preencher(conta.email)}
                >
                  <span>{conta.email}</span>
                  <span className="conta-papel">{conta.papel}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
