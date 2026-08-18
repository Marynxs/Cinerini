import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { Layout, Voltar } from '../components/Layout';
import './Login.css';

/* Contas do seed, para quem avalia não precisar digitar.

   Aparecem também em produção. Escondê-las lá seria teatro: as mesmas
   credenciais estão publicadas no README de um repositório público, então a
   omissão na tela não protegeria nada e cobraria de quem avalia uma ida ao
   GitHub no primeiro minuto de uso.

   O que a decisão aceita é vandalismo — entrar como organizador e cancelar
   sessões. Fica aceito porque o estrago se desfaz com `python -m app.seed
   --reset`, e porque o rótulo declara que este é um ambiente de
   demonstração em vez de fingir que é produção. */
const CONTAS_SEMEADAS = [
  { papel: 'Organizador', email: 'organizador@cinerini.com.br' },
  { papel: 'Cliente', email: 'cliente1@cinerini.com.br' },
  { papel: 'Cliente', email: 'cliente2@cinerini.com.br' },
  { papel: 'Funcionário', email: 'portaria@cinerini.com.br' },
];

const SENHA_SEMEADA = 'cinerini123';

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

      // Cada papel cai onde tem trabalho a fazer. O cliente é o único que
      // volta ao ponto de origem, porque é o único que estava no meio de
      // alguma coisa quando o login foi exigido.
      const inicio = {
        customer: destino,
        organizer: '/painel',
        gate: '/portaria',
      }[usuario.role] ?? '/';

      navegar(inicio, { replace: true });
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

          <div className="contas">
            <p className="contas-titulo">Ambiente de demonstração</p>
            <p className="contas-nota">
              Clique numa conta para preencher. Senha de todas:{' '}
              <strong>{SENHA_SEMEADA}</strong>
            </p>

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
        </div>
      </div>
    </Layout>
  );
}
