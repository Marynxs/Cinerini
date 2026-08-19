# Cinerini

Plataforma de eventos e ingressos de cinema. O organizador publica sessões a partir do catálogo do TMDb, o cliente escolhe a poltrona num mapa e paga (simulado), recebe um ingresso com código em QR e pode compartilhá-lo por link. Na entrada, a portaria valida o ingresso.

![Compra de um ingresso do catálogo à poltrona, e a validação do QR na portaria](Cinerini.gif)

*Cinerini* — cinema + Marini (meu sobrenome).

**No ar:** [cinerini.vercel.app](https://cinerini.vercel.app) · API em [cinerini-api.onrender.com](https://cinerini-api.onrender.com) ([`/docs`](https://cinerini-api.onrender.com/docs))

As contas de teste e o cartão que reprova o pagamento estão logo abaixo. A primeira visita pode levar até um minuto: o plano gratuito hiberna, e a própria tela explica isso enquanto religa.

---

## O problema que o sistema resolve

**Um lugar não pode ser vendido duas vezes**, mesmo com duas pessoas clicando na mesma poltrona no mesmo milissegundo. **Um ingresso não pode entrar duas vezes**, mesmo que o QR seja lido em dois leitores ao mesmo tempo.

As quatro garantias abaixo são a espinha do projeto, e cada uma vive no lugar onde não pode ser burlada.

### 1. Assento nunca vendido duas vezes

```sql
CREATE UNIQUE INDEX uq_seat_ocupado ON tickets (seat_id)
  WHERE status <> 'cancelled'
```

A reserva **não consulta a disponibilidade antes de inserir**. Ela tenta inserir e deixa o banco arbitrar. O motivo é que entre um `SELECT` que verifica e um `INSERT` que reserva cabe outra transação inteira: duas pessoas consultariam, ambas veriam "livre", ambas inseririam. Nenhuma quantidade de código de aplicação fecha essa janela — a constraint fecha, porque verificação e escrita acontecem no mesmo passo atômico. Quem perde recebe `IntegrityError`, traduzido em qual poltrona foi perdida.

O índice é **parcial** para que o cancelamento devolva o assento ao estoque sem código adicional: a linha cancelada sai do índice e a poltrona volta a ser vendável.

### 2. QR não forjável

O código dentro do QR é um JWT assinado com a chave do servidor, contendo o identificador público do ingresso e a exibição a que ele pertence. Sem a chave não há como produzir um código aceito.

O token **não expira**: quem decide se o ingresso vale é a portaria consultando o banco. Prazo no token criaria uma segunda fonte de verdade sobre validade, e duas fontes divergem.

### 3. Ingresso não validado duas vezes

```sql
UPDATE tickets SET status='used', used_at=now()
WHERE id = :id AND status='valid'
```

Zero linhas afetadas significa que já foi usado. Nunca um `SELECT` seguido de `UPDATE`, que teria a mesma janela de corrida do item 1.

### 4. Ingresso do lugar errado é estado próprio

A conta é de um funcionário e pertence a um cinema; ele escolhe a **exibição** do turno entre as daquele cinema — aquele filme, naquele horário, naquela sala (D24). Ingresso legítimo que não pertence a ela retorna um estado distinto de "inválido", e são dois: `wrong_event` para outro filme, `wrong_showing` para outra sessão do mesmo filme. Situações diferentes exigem reações diferentes de quem está na entrada — uma manda a pessoa para outra sala, a outra para outro horário.

O vínculo é pela exibição e não pelo filme porque o filme passa em vários horários e cinemas: amarrado nele, a portaria das 19h aceitaria o ingresso das 22h, e a pessoa sentaria numa poltrona vendida a outro comprador. Decisão registrada como D21, junto com a alternativa descartada.

A exibição é conferida **antes** do estado do ingresso. Na ordem inversa, recusar alguém na porta errada já teria consumido um ingresso que a portaria certa ainda precisa aceitar.

---

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Front | React + Vite, TypeScript | Sem SSR: o back-end é o FastAPI, e o Next.js só somaria conceito |
| Estilo | CSS puro com variáveis | Framework de estilo traz a estética dele junto, que é a cara que o desafio manda evitar |
| Back | FastAPI + SQLAlchemy 2.0 + Alembic | Validação por anotação de tipo, OpenAPI automático, migrations versionadas |
| Banco | PostgreSQL 18 (Neon) | As garantias vivem em constraints, e índice parcial é recurso dele |
| Auth | PyJWT (HS256) + bcrypt | Sem `passlib` nem `python-jose`: o primeiro quebra com bcrypt 5.x, o segundo está sem manutenção |
| Catálogo | TMDb | Filme em cartaz → sessão → poltrona é a cadeia que justifica o mapa de assentos |

---

## Como executar

### Com Docker, num comando

```bash
docker compose up --build
```

Front em **http://localhost:5173**, API em **http://localhost:8000**, documentação interativa em **/docs**. A primeira subida leva alguns minutos construindo as imagens e ocupa cerca de 850 MB; as seguintes são imediatas.

Sobe um PostgreSQL próprio em contêiner, aplica as migrations e semeia o cenário de teste antes de abrir a porta. **Não usa credencial nenhuma da máquina**: o banco é o contêiner ao lado, a chave que assina os ingressos é um valor de desenvolvimento declarado no `docker-compose.yml`, e o `.env` local fica de fora pelos `.dockerignore`.

A chave do TMDb é opcional: sem ela o seed cai para a ficha embutida, que tem título, sinopse e duração, mas **não traz pôster** — o catálogo aparece sem as imagens, e a busca de filmes pelo organizador fica indisponível. Todo o resto do fluxo funciona igual. Para usar a sua:

```bash
TMDB_API_KEY=sua-chave docker compose up --build
```

Para apagar o banco e semear do zero: `docker compose down -v`.

### Sem Docker

Requisitos: **Python 3.13 ou 3.14 (64-bit)**, **Node 20+** e um banco PostgreSQL.

### 1. Banco

Crie um banco PostgreSQL. A forma mais rápida é o plano gratuito da [Neon](https://neon.com), que devolve uma string de conexão pronta. Um Postgres local também serve.

### 2. API

```bash
cd api
python -m venv .venv
.venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # preencha DATABASE_URL e SECRET_KEY
alembic upgrade head          # cria as tabelas
python -m app.seed            # popula o cenário de teste
python dev.py                 # sobe em http://localhost:8000
```

Gere a `SECRET_KEY` com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

A documentação interativa da API fica em **http://localhost:8000/docs**.

### 3. Front

```bash
cd web
npm install
cp .env.example .env          # VITE_API_URL aponta para a API
npm run dev                   # sobe em http://localhost:5173
```

---

## Deploy

Três serviços, todos em plano gratuito. O porquê de cada um está em `docs/DECISOES.md` como D17.

| Serviço | O quê | Configuração |
|---|---|---|
| Neon | PostgreSQL | Fora do Render de propósito: o Postgres gratuito de lá expira em 30 dias |
| Render | API | `render.yaml`, na raiz |
| Vercel | Front | `web/vercel.json`, com *Root Directory* em `web/` |

**API.** No Render, *New → Blueprint*, apontando para o repositório. O `render.yaml` declara build, start, health check e as variáveis; as marcadas `sync: false` são preenchidas no painel — `DATABASE_URL` (a string do Neon, com o driver `postgresql+psycopg`), `TMDB_API_KEY` e `CORS_ORIGINS`. O `SECRET_KEY` é gerado uma vez na criação: **trocá-lo invalida todo QR já emitido**, porque é ele que assina os códigos de ingresso.

A migration roda no build. O seed **não** roda no Render: o plano gratuito não dá acesso ao shell do serviço, e não precisa — o banco é o mesmo Neon usado no desenvolvimento, então `python -m app.seed` executado da máquina local popula a instância que a produção lê.

Um banco só para os dois ambientes é escolha de escopo, não descuido: o sistema não guarda dado real e existe para ser percorrido. Num sistema em uso seriam dois bancos, e o seed teria de rodar por um job de deploy em vez de por uma máquina de desenvolvimento.

**Front.** Na Vercel, importar o repositório com *Root Directory* em `web/`. Uma variável: `VITE_API_URL`, com a URL do serviço no Render. O `vercel.json` existe por um motivo só — o roteamento é do lado do cliente, e sem a reescrita para `index.html` qualquer link direto para `/meus-ingressos` cairia em 404 do servidor estático.

**Ordem.** O front precisa da URL da API, e o `CORS_ORIGINS` da API precisa do domínio do front. Sobe a API primeiro com um valor provisório, publica o front, e volta para corrigir o `CORS_ORIGINS` com o domínio definitivo.

**Hibernação.** O plano gratuito do Render dorme após 15 minutos parado, e religar leva dezenas de segundos. Três camadas tratam isso, e nenhuma resolve sozinha:

1. O front chama `/health` assim que a página monta, gastando o religamento enquanto a pessoa ainda lê a tela.
2. Um agendamento do GitHub Actions (`.github/workflows/manter-api-acordada.yml`) mantém o serviço acordado das 8h às 23h — é o que cobre o primeiro visitante do dia, que a camada anterior não alcança. Exige a variável de repositório `API_URL`, em *Settings → Secrets and variables → Actions → Variables*.
3. Passados quatro segundos, a tela de carregamento explica o motivo da espera. Dizer o porquê é o que separa "está lento" de "está quebrado".

---

## Contas de teste

Criadas pelo seed. Senha de todas: **`cinerini123`**

A tela de login lista as quatro e preenche o formulário num clique — inclusive no ambiente publicado. Escondê-las lá seria teatro, já que esta seção as publica de qualquer forma (D18).

| Papel | E-mail | O que faz |
|---|---|---|
| Organizador | `organizador@cinerini.com.br` | Cadastra cinemas, salas, eventos e sessões; publica, cancela e também valida na portaria |
| Cliente | `cliente1@cinerini.com.br` | Compra, vê ingressos, compartilha e cancela |
| Cliente | `cliente2@cinerini.com.br` | Serve para demonstrar a disputa por poltrona |
| Funcionário | `portaria@cinerini.com.br` | Abre a portaria, escolhe a sessão do turno e valida os ingressos dela |

O seed cria 2 cinemas em cidades diferentes, 3 salas, 3 filmes do TMDb e 11 sessões. Um dos filmes passa **nos dois cinemas**, para que o agrupamento por cinema e o filtro por cidade sejam perceptíveis.

A portaria trabalha no Cine Belas Artes e **nasce sem turno escolhido**: ao entrar, ela escolhe qual sessão está atendendo. Esse cinema dá os dois recusados de uma vez — as demais sessões do mesmo filme demonstram **outra sessão**, e um ingresso de qualquer outro filme demonstra **outro evento**.

Contas de funcionário são criadas pelo organizador, na aba *Equipe* do painel, escolhendo o **cinema**. Qual sessão a pessoa atende é decisão dela, a cada turno (D24).

**Para criar um organizador:** numa instalação vazia, o primeiro cadastro nasce organizador. Havendo um, ele promove um funcionário escolhido em lista, na aba *Equipe* do painel. Quem é promovido deixa de ser funcionário, e revogar o papel o devolve à equipe — as duas operações se desfazem uma à outra (D32). Não há comando de linha para isso porque o plano gratuito do Render não dá acesso ao shell, e um comando deixaria a instalação publicada sem caminho nenhum (D22).

**Para validar sem dois aparelhos:** cada ingresso mostra, embaixo do QR, o código para digitação. Abra "Meus ingressos" numa aba, copie o código, e cole no campo da portaria em outra. A digitação existe para quando a câmera falha, e serve igualmente para demonstrar num computador só (D20).

O seed é idempotente — rodar duas vezes não duplica nada. Para refazer do zero: `python -m app.seed --reset`.

---

## Pagamento

A cobrança é **simulada**, sem transação financeira real. O desfecho é determinístico para que ambos os caminhos sejam demonstráveis quando se quiser, e não quando a sorte permitir:

| Cartão | Resultado |
|---|---|
| `4111 1111 1111 1111` | Aprovado |
| `4111 1111 1111 1110` | **Recusado** — qualquer cartão terminado em zero |

Os dois aparecem na própria tela de pagamento, clicáveis.

**Sobre usar um provedor real.** O enunciado permite o ambiente de testes de um provedor de verdade. O módulo `api/app/payment.py` isola a decisão numa função com a assinatura que um provedor real usaria — inclusive o valor, que a simulação não consulta. Trocar por Stripe em modo de teste exigiria implementar `charge` e um webhook de confirmação, sem alterar o fluxo de reserva.

Não foi feito por duas razões: colocaria um serviço externo no caminho crítico que o avaliador precisa percorrer, e a tela de pagamento hospedada substituiria a identidade visual do projeto pela do provedor, justamente no passo mais importante da compra.

---

## Testes

```bash
cd api
pytest                  # 267 casos, sem rede e sem chave do TMDb
pytest -m contract      # 3 casos contra o TMDb real, precisa de chave
```

Cada teste roda dentro de uma transação desfeita ao final, com savepoints para que o `commit` do código sob teste funcione sem persistir. Isso permite rodar a suíte **contra o mesmo banco de desenvolvimento sem destruir os dados semeados**.

As garantias são testadas contra o schema, não contra rotas: um dos casos consulta o `pg_indexes` e confirma que o índice existe com a cláusula `WHERE`. Uma rota pode ser reescrita; a regra não pode ser enfraquecida sem quebrar esse teste.

O TMDb é substituído por um duplo na suíte padrão — teste que depende de rede é lento, quebra sem internet e falha para quem não tem chave. Como o duplo concorda consigo mesmo por definição, os três testes de contrato batem na API real e verificam só o formato da resposta.

---

## Chave do TMDb

Só é necessária para **rodar localmente** e afeta apenas a busca de filmes pelo organizador. Todo o resto do fluxo funciona sem ela: os dados do filme são copiados para a tabela `events` no momento da publicação, e o seed tem uma ficha embutida de reserva caso a API do TMDb não responda.

Obtenha em [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) — é gratuita e sai na hora. Use a **API Key (v3 auth)**, a chave curta.

---

## Limitações conhecidas

Declaradas porque existem, não porque passaram despercebidas.

**Enumeração de usuários no cadastro.** Ao tentar criar conta com um e-mail já usado, a resposta confirma que a conta existe. Esconder isso exigiria confirmação por e-mail, listado como fora de escopo — e sem esse canal, esconder trocaria o vazamento por um usuário travado sem entender por que o cadastro não conclui. A exposição é compensada por limite de tentativas por IP e por conta. Registrado em `docs/DECISOES.md` como D8.

**O limitador de tentativas vive em memória.** A contagem zera quando o processo reinicia. Persistir em banco custaria uma escrita por tentativa de login, o que transformaria o próprio limitador em vetor de esgotamento de disco. É mitigação de custo, não bloqueio absoluto.

**O cache do TMDb também é em memória**, com prazo de seis horas e teto de 200 entradas. Some quando o processo reinicia, e isso é aceitável: o catálogo do cliente não depende dele.

**Não há recuperação de senha**, nem envio de e-mail, nem nota fiscal, nem revenda entre usuários — todos fora de escopo pelo enunciado.

**Um banco serve desenvolvimento e produção.** A consequência é concreta e já aconteceu: aplicar uma migration na máquina de desenvolvimento altera o schema que a produção lê, e a API publicada continua rodando o código anterior até o próximo deploy. Nessa janela toda consulta à tabela alterada falha. A ordem segura é publicar o código antes de migrar, ou aceitar a janela sabendo que ela existe. Dois bancos resolveriam, ao custo de manter dois seeds e duas cadeias de migration por dois dados que não são reais.

**Cinemas não têm dono.** Qualquer organizador cadastra, edita e remove cinema, sala e funcionário — inclusive de outro organizador. Eventos e sessões são protegidos por dono, o cadastro de locais não. É o que impede abrir o cadastro de organizador ao público, como fazem Sympla e Eventbrite: sem cercar o local primeiro, o catálogo ficaria à mercê de quem aparecesse. O caminho é dar `organizer_id` ao `Venue`, e não foi percorrido por escopo (D22).

**A lista de municípios depende do IBGE.** Se a API de localidades estiver fora, não dá para cadastrar cinema novo — e nada mais: catálogo, compra e portaria não passam por lá. A resposta nesse caso diz o que aconteceu, e o seed traz os códigos escritos para semear sem internet (D23).

**Só há mapa de assentos.** O desafio pede um dos dois modos, e a escolha foi assento numerado por ser onde a garantia de unicidade aparece de verdade.

---

## Documentação do projeto

| Arquivo | O que responde |
|---|---|
| `docs/ESPECIFICACAO.md` | O que o sistema faz e quando está pronto |
| `docs/DECISOES.md` | Por que faz assim, e o que foi descartado — 31 decisões |
| `CLAUDE.md` | Contexto que restringe o agente de IA: garantias, tokens visuais, convenções |
| `AI-USAGE.md` | Como a IA foi conduzida e onde a saída dela foi corrigida |
| `Prototipos/` | Protótipo da sala de cinema desenhado antes da tela existir |

---

## Identidade visual

Direção **recibo térmico**: papel creme, tipografia monoespaçada, alinhamentos de cupom fiscal, tracejado como divisor. Seis cores no total.

A escolha não é estética por si só — o objeto que o sistema produz **é um bilhete**, e a interface adota a linguagem do próprio objeto. O ingresso na tela tem picote com recorte, corpo e canhoto.

Uma regra sustenta a paleta: o carmim `#A32B1C` é **reservado** a ação e atenção — poltrona selecionada, erro, recusa. Se aparecer como decoração, está errado.

Os cinco estados de assento se distinguem por **forma e textura além de cor**: livre é contorno, ocupada é preenchida, em espera é hachurada, a sua tem marca de conferido, e acessível é círculo com o símbolo internacional. Tirando a cor da tela, o mapa continua utilizável — o par carmim/bege é indistinguível para parte das pessoas.

A única exceção ao monoespaçado é a sinopse vinda do TMDb, em fonte proporcional. Mono alinha dado tabular sozinho e perde em prosa corrida; a sinopse é o único texto longo do sistema.
