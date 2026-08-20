# Contexto do projeto

Arquivo de contexto que orienta o agente de IA usado no desenvolvimento. Versionado deliberadamente: mostra como a ferramenta foi conduzida.

## O que é

**Cinerini** é uma plataforma de eventos e ingressos de cinema. Organizador publica sessões a partir do catálogo do TMDb, cliente escolhe poltrona e paga (simulado), recebe ingresso com QR, portaria valida na entrada.

Especificação em `docs/ESPECIFICACAO.md`. Decisões em `docs/DECISOES.md`.

## Stack

- **Front:** React + Vite (`web/`)
- **Back:** FastAPI + SQLAlchemy 2.0 + Alembic (`api/`)
- **Banco:** PostgreSQL 18 no Neon
- **Auth:** PyJWT (HS256) e bcrypt direto. Não usar passlib nem python-jose

## Garantias inegociáveis

Quatro invariantes. Nenhuma alteração pode enfraquecê-las.

1. **Assento nunca vendido duas vezes.** Índice único parcial `tickets(seat_id) WHERE status <> 'cancelled'`. A garantia vive no banco, não na aplicação. Nunca substituir por verificação em Python.
2. **QR não forjável.** O código é um JWT assinado com `SECRET_KEY`. Nunca expor identificador previsível no lugar dele.
3. **Ingresso não validado duas vezes.** `UPDATE ... WHERE status='valid'` conferindo linhas afetadas. Nunca `SELECT` seguido de `UPDATE`.
4. **Ingresso do lugar errado é estado próprio.** Portaria vinculada a `gate_showing_id`, que é a exibição e não o filme (D21). Divergência não pode colapsar em "inválido", e separa dois casos: outro filme e outra sessão do mesmo filme. O escopo do funcionário é `gate_venue_id`, e o turno é escolha dele (D24).

## Identidade visual

Direção **recibo térmico**: papel, monoespaçado, alinhamentos de cupom fiscal, tracejado como divisor.

| Token | Valor | Uso |
|---|---|---|
| `papel` | `#F2EDE2` | fundo de superfície |
| `papel-fundo` | `#E4DCCB` | fundo da página |
| `tinta` | `#191512` | texto e ações primárias |
| `tinta-fraca` | `#7A6C58` | metadados e rótulos |
| `picote` | `#A99B84` | divisores tracejados |
| `carimbo` | `#A32B1C` | **reservado**: seleção, erro, recusa |

- Tipografia: **IBM Plex Mono** em todo o sistema. Única exceção: sinopse do TMDb em **IBM Plex Sans**.
- Escala: display 26/600/uppercase · título 15/600 · corpo 12.5/400 · etiqueta 9/400/`0.16em`
- O carmim nunca é decoração. Se aparecer sem indicar ação ou atenção, está errado.
- Estados de assento se distinguem por **forma e textura além de cor**, porque o par carmim/bege é indistinguível para parte dos usuários.

## Convenções

- Documentação, comentários e mensagens de commit em **português**. Código e identificadores em inglês.
- Valores monetários em **centavos, como inteiro**. Nunca float.
- `Showing` é a exibição; `Session` é reservado ao SQLAlchemy.
- Papel nunca vem do corpo da requisição. Portaria é criada pelo organizador, organizador é promovido por outro (D22).
- Cidade e UF nunca são texto livre: vêm de lista, e o nome é resolvido no servidor contra o IBGE (D23).
- Comentário no código explica **por que**, nunca o que a linha faz.
- Classe onde há estado ou identidade a proteger; função de módulo onde não há (D11). Regra de negócio em módulo próprio, fora do handler de rota. Sem camada de repositório sobre o SQLAlchemy.
- Coleção sob o recurso pai, item na raiz: `/events/{id}/showings` para listar e criar, `/showings/{id}` para operar sobre uma (D12).
- Nenhum arquivo do repositório contém conteúdo introdutório ou didático. A documentação é escrita para quem domina a stack: decisões e trade-offs, não definições.

## Verificação

Verificar sempre contra o artefato que vai para produção, nunca contra um substituto conveniente. Três episódios do dia 4 vieram de ignorar isso:

- `npm run build` no front, **nunca** `tsc --noEmit`: o `tsconfig` do projeto tem `erasableSyntaxOnly`, que o `--noEmit` avulso não aplica.
- API subida por `python dev.py`, que recusa começar se a porta estiver ocupada. `uvicorn --reload` encerrado à força deixa processo filho vivo herdando o socket, e vários servidores passam a dividir a porta com versões diferentes do código em memória.
- Percurso ponta a ponta por HTTP contra o servidor rodando, e não pelo `TestClient` em processo. Só o primeiro exercita serialização, CORS e o contrato realmente publicado.
- Alteração em qualquer arquivo da API só está verificada depois de o processo reiniciar. Ele carrega o que existia ao subir, e o sintoma muda com o que mudou: **schema** faltando chega no front como `undefined`, sem erro; **rota** renomeada faz o caminho novo casar com o antigo, e `/events/managed` caiu em `/events/{event_id}` e devolveu *"unable to parse string as an integer"*, apontando para o front quando a causa era o servidor.
- Latência medida em produção, nunca no `localhost`. O custo de N+1 é o número de idas ao banco, e na mesma máquina a ida é quase de graça: 39 consultas somavam 0,62s aqui e 9s com a API no Render e o banco no Neon. Rota que devolve coleção tem o custo de idas fixado em teste (D37).
Antes de afirmar que algo funciona, conferir o contrato servido em `/openapi.json`, não o schema no arquivo.

## Commits

Conventional commits com escopo, em português, imperativo. Uma unidade de trabalho por commit, nunca agrupando features distintas.

**Assunto:** até 50 caracteres. **Corpo:** quebrado em 72 colunas, e só quando a decisão não é óbvia lendo o diff. Nesse caso, de 2 a 5 linhas, explicando o porquê e nunca o como. Mudança mecânica (renomear, formatar, ajustar dependência) fica só com o assunto. Quando houver decisão registrada em `docs/DECISOES.md`, o corpo aponta para o `D#` em vez de repetir o texto: duas fontes para a mesma justificativa divergem.

Nos commits que tocam as quatro garantias, o corpo registra a alternativa descartada e o motivo.

Alterações em `AI-USAGE.md` entram no mesmo commit da mudança que registram, nunca em commit próprio, porque o registro e o fato são a mesma unidade de trabalho.

## Fora de escopo

Nota fiscal, revenda entre usuários, aplicativo nativo, recuperação de senha, envio de ingresso por e-mail.
