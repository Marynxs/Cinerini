# Cinerini

Plataforma de eventos e ingressos de cinema. O organizador publica sessões a partir do catálogo do TMDb, o cliente escolhe a poltrona num mapa e paga (simulado), recebe um ingresso com código em QR e pode compartilhá-lo por link. Na entrada, a portaria valida o ingresso.

![Compra de um ingresso do catálogo à poltrona, e a validação do QR na portaria](Cinerini.gif)

*Cinerini*: cinema + Marini (meu sobrenome).

**No ar:** [cinerini.vercel.app](https://cinerini.vercel.app) · API na AWS em [54-157-43-152.sslip.io](https://54-157-43-152.sslip.io) ([`/docs`](https://54-157-43-152.sslip.io/docs))

As contas de teste e o cartão que reprova o pagamento estão logo abaixo.

---

## O problema que o sistema resolve

**Um lugar não pode ser vendido duas vezes**, mesmo com duas pessoas clicando na mesma poltrona no mesmo milissegundo. **Um ingresso não pode entrar duas vezes**, mesmo que o QR seja lido em dois leitores ao mesmo tempo.

As quatro garantias abaixo são a espinha do projeto, e cada uma vive no lugar onde não pode ser burlada.

### 1. Assento nunca vendido duas vezes

```sql
CREATE UNIQUE INDEX uq_seat_ocupado ON tickets (seat_id)
  WHERE status <> 'cancelled'
```

A reserva **não consulta a disponibilidade antes de inserir**. Ela tenta inserir e deixa o banco arbitrar. O motivo é que entre um `SELECT` que verifica e um `INSERT` que reserva cabe outra transação inteira: duas pessoas consultariam, ambas veriam "livre", ambas inseririam. Nenhuma quantidade de código de aplicação fecha essa janela. A constraint fecha, porque verificação e escrita acontecem no mesmo passo atômico. Quem perde recebe `IntegrityError`, traduzido em qual poltrona foi perdida.

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

A conta é de um funcionário e pertence a um cinema; ele escolhe a **exibição** do turno entre as daquele cinema: aquele filme, naquele horário, naquela sala (D24). Ingresso legítimo que não pertence a ela retorna um estado distinto de "inválido", e são dois: `wrong_event` para outro filme, `wrong_showing` para outra sessão do mesmo filme. Situações diferentes exigem reações diferentes de quem está na entrada, porque uma manda a pessoa para outra sala e a outra para outro horário.

O vínculo é pela exibição e não pelo filme porque o filme passa em vários horários e cinemas: amarrado nele, a portaria das 19h aceitaria o ingresso das 22h, e a pessoa sentaria numa poltrona vendida a outro comprador. Decisão registrada como D21, junto com a alternativa descartada.

A exibição é conferida **antes** do estado do ingresso. Na ordem inversa, recusar alguém na porta errada já teria consumido um ingresso que a portaria certa ainda precisa aceitar.

---

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Front | React + Vite, TypeScript | Sem SSR: o back-end é o FastAPI, e o Next.js só somaria conceito |
| Estilo | CSS puro com variáveis | Framework de estilo traz a estética dele junto, que é a cara que o desafio manda evitar |
| Back | FastAPI + SQLAlchemy 2.0 + Alembic | Validação por anotação de tipo, OpenAPI automático, migrations versionadas |
| Banco | PostgreSQL 18 (Amazon RDS) | As garantias vivem em constraints, e índice parcial é recurso dele |
| Infra | AWS (EC2, RDS, ECR), Terraform, GitHub Actions | Infraestrutura declarada e recriável com um comando; deploy sem chave de acesso guardada |
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

A chave do TMDb é opcional: sem ela o seed cai para a ficha embutida, que tem título, sinopse e duração, mas **não traz pôster**, então o catálogo aparece sem as imagens, e a busca de filmes pelo organizador fica indisponível. Todo o resto do fluxo funciona igual. Para usar a sua:

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

API e banco na AWS, front na Vercel. A operação completa (arquitetura, custo, segredos, deploy, rollback e como apagar tudo) está em [`docs/deploy-aws.md`](docs/deploy-aws.md); o porquê, na D38.

| Peça | Onde | Configuração |
|---|---|---|
| API | EC2 t4g.micro, atrás do Caddy com TLS automático | `deploy/`, `infra/ec2.tf` |
| Banco | RDS PostgreSQL 18, sem IP público, mesma zona da EC2 | `infra/rds.tf` |
| Imagem | ECR, tag imutável por commit | `infra/ecr.tf` |
| Pipeline | GitHub Actions: testes, build arm64, varredura com Trivy, deploy por SSM | `.github/workflows/deploy-aws.yml` |
| Verificação da infra | GitHub Actions: `fmt`, `validate`, `tflint`, `checkov` | `.github/workflows/infra.yml` |
| Estado do Terraform | S3 versionado, com trava | `infra/bootstrap/` |
| Reset do demo | EventBridge Scheduler → Lambda → SSM, todo dia às 4h | `infra/demo_reset.tf` |
| Monitoramento | CloudWatch: logs JSON, painel com SLO, alarmes por e-mail | `infra/dashboard.tf`, `infra/monitoring.tf` |
| Dependências | Dependabot: pip, npm, Docker, Actions, Terraform | `.github/dependabot.yml` |
| Front | Vercel | `web/vercel.json`, com *Root Directory* em `web/` |

**Infraestrutura em Terraform.** `terraform apply` em `infra/` cria tudo, e `terraform destroy` apaga tudo. Custo estimado de US$ 25 por mês, sem NAT Gateway nem Load Balancer.

**Deploy a cada push na `main`.** O workflow roda a suíte num Postgres 18, publica a imagem no ECR e manda a EC2 baixá-la, migrar e trocar o contêiner. Não há chave da AWS no GitHub: cada execução troca um token OIDC por credenciais de minutos, aceitas só para a `main` deste repositório. A migration roda antes da troca, e falhando a versão anterior segue no ar.

**Segredos no SSM Parameter Store**, nunca no repositório nem no estado do Terraform. O `SECRET_KEY` assina os códigos de ingresso: **trocá-lo invalida todo QR já emitido**, e a API recusa subir com chave menor que 32 bytes, o mínimo do HS256.

**A imagem é varrida antes de publicar.** O Trivy reprova vulnerabilidade alta ou crítica com correção disponível, e a imagem reprovada não chega ao ECR. Se a versão nova sobe e não responde por HTTPS, o deploy volta sozinho para a anterior.

**Operação.** Logs em JSON no CloudWatch, painel com SLO de 99% de disponibilidade, alarmes por e-mail (saúde, 5xx, CPU, tráfego de saída), estado do Terraform no S3 com trava, e o Terraform verificado no CI por `tflint` e `checkov`. Detalhes em [`docs/deploy-aws.md`](docs/deploy-aws.md).

**Front.** Na Vercel, importar o repositório com *Root Directory* em `web/`. Uma variável: `VITE_API_URL`, com o endereço da API. O `vercel.json` existe por um motivo só: o roteamento é do lado do cliente, e sem a reescrita para `index.html` qualquer link direto para `/meus-ingressos` cairia em 404 do servidor estático.

**Reserva no Render.** O `render.yaml` continua válido e sobe a API com banco no Neon, como antes da AWS (D17). Voltar para ele é trocar o `VITE_API_URL` da Vercel.

---

## Contas de teste

Criadas pelo seed. Senha de todas: **`cinerini123`**

A tela de login lista as quatro e preenche o formulário num clique, inclusive no ambiente publicado. Escondê-las lá seria teatro, já que esta seção as publica de qualquer forma (D18).

| Papel | E-mail | O que faz |
|---|---|---|
| Organizador | `organizador@cinerini.com.br` | Cadastra cinemas, salas, eventos e sessões; publica, cancela e também valida na portaria |
| Cliente | `cliente1@cinerini.com.br` | Compra, vê ingressos, compartilha e cancela |
| Cliente | `cliente2@cinerini.com.br` | Serve para demonstrar a disputa por poltrona |
| Funcionário | `portaria@cinerini.com.br` | Abre a portaria, escolhe a sessão do turno e valida os ingressos dela |

O seed cria 2 cinemas em cidades diferentes, 3 salas, 3 filmes do TMDb e 35 sessões. Um dos filmes passa **nos dois cinemas**, para que o agrupamento por cinema e o filtro por cidade sejam perceptíveis.

As sessões são semeadas a cada dois dias pelas três semanas seguintes ao dia em que o comando roda. O passo é curto porque a portaria só oferece turnos dentro da janela dela, e o horizonte é longo porque o catálogo só lista sessão futura: com a agenda apertada, um banco semeado numa segunda amanhecia vazio na quinta.

A portaria trabalha no Cine Belas Artes e **nasce sem turno escolhido**: ao entrar, ela escolhe qual sessão está atendendo. Esse cinema dá os dois recusados de uma vez: as demais sessões do mesmo filme demonstram **outra sessão**, e um ingresso de qualquer outro filme demonstra **outro evento**.

Contas de funcionário são criadas pelo organizador, na aba *Equipe* do painel, escolhendo o **cinema**. Qual sessão a pessoa atende é decisão dela, a cada turno (D24).

**Para criar um organizador:** numa instalação vazia, o primeiro cadastro nasce organizador. Havendo um, ele promove um funcionário escolhido em lista, na aba *Equipe* do painel. Quem é promovido deixa de ser funcionário, e revogar o papel o devolve à equipe, de modo que as duas operações se desfazem uma à outra (D32). Não há comando de linha para isso: o caminho é o da interface, que existe em qualquer instalação (D22).

**Para validar sem dois aparelhos:** cada ingresso mostra, embaixo do QR, o código para digitação. Abra "Meus ingressos" numa aba, copie o código, e cole no campo da portaria em outra. A digitação existe para quando a câmera falha, e serve igualmente para demonstrar num computador só (D20).

O seed é idempotente, e rodar duas vezes não duplica nada. Para refazer do zero: `python -m app.seed --reset`.

**No ambiente publicado, tudo volta ao seed toda madrugada.** As contas são públicas e o organizador pode apagar o que quiser; o reset diário desfaz o estrago e recalcula as sessões a partir do dia (D40). Ingresso comprado lá dura até as 4h.

---

## Pagamento

A cobrança é **simulada**, sem transação financeira real. O desfecho é determinístico para que ambos os caminhos sejam demonstráveis quando se quiser, e não quando a sorte permitir:

| Cartão | Resultado |
|---|---|
| `4111 1111 1111 1111` | Aprovado |
| `4111 1111 1111 1110` | **Recusado** (qualquer cartão terminado em zero) |

Os dois aparecem na própria tela de pagamento, clicáveis.

**Sobre usar um provedor real.** O enunciado permite o ambiente de testes de um provedor de verdade. O módulo `api/app/payment.py` isola a decisão numa função com a assinatura que um provedor real usaria, inclusive o valor, que a simulação não consulta. Trocar por Stripe em modo de teste exigiria implementar `charge` e um webhook de confirmação, sem alterar o fluxo de reserva.

Não foi feito por duas razões: colocaria um serviço externo no caminho crítico que o avaliador precisa percorrer, e a tela de pagamento hospedada substituiria a identidade visual do projeto pela do provedor, justamente no passo mais importante da compra.

---

## Testes

### API

```bash
cd api
pytest                  # 290 casos, sem rede e sem chave do TMDb
pytest -m contract      # 3 casos contra o TMDb real, precisa de chave
```

Cada teste roda dentro de uma transação desfeita ao final, com savepoints para que o `commit` do código sob teste funcione sem persistir. Isso permite rodar a suíte **contra o mesmo banco de desenvolvimento sem destruir os dados semeados**.

No GitHub, a suíte roda a cada push num Postgres 18 vazio, só com as migrations (`.github/workflows/ci.yml`), e é a primeira etapa do deploy. O banco vazio é o que pega teste que só passava por contar com o seed.

As garantias são testadas contra o schema, não contra rotas: um dos casos consulta o `pg_indexes` e confirma que o índice existe com a cláusula `WHERE`. Uma rota pode ser reescrita; a regra não pode ser enfraquecida sem quebrar esse teste.

O TMDb é substituído por um duplo na suíte padrão, porque teste que depende de rede é lento, quebra sem internet e falha para quem não tem chave. Como o duplo concorda consigo mesmo por definição, os três testes de contrato batem na API real e verificam só o formato da resposta.

### Carga, com k6

A garantia 1 testada sob concorrência real: 500 clientes diferentes reservando **a mesma poltrona no mesmo instante**.

| Resultado | |
|---|---|
| Reservas aceitas | **1** |
| Recusadas com 409 | 499 |
| Erros ou outros status | 0 |
| Ingressos no banco para a poltrona | **1** |

Rodado no compose de produção, com Postgres 18 (`loadtest/`, procedimento em `docs/deploy-aws.md`). A primeira execução não vendeu nada: todas as requisições travaram até o tempo limite do pool de conexões, num deadlock entre as threads do FastAPI e as conexões do SQLAlchemy que só aparece acima de algumas dezenas de requisições simultâneas. O defeito e a correção estão na D39.

A suíte não enxerga esse tipo de defeito, porque faz uma requisição por vez. Por isso a corrida roda de novo sempre que muda o pool, o teto de requisições em andamento ou as bibliotecas que os controlam, como na atualização do SQLAlchemy 2.0 para 2.1, aprovada com o mesmo resultado acima.

Contra a AWS, a leitura do catálogo responde com **p95 de 291 ms vista do Brasil e de 13 ms dentro do servidor**, sem nenhum erro em 232 requisições. A diferença é a distância até a Virgínia: a API responde em cerca de 11 ms, e o resto é rede.

### Dependências

O Dependabot abre, toda semana, um pull request por ecossistema: bibliotecas da API, do front, imagem base, Actions e providers do Terraform. Correção de segurança vem fora do calendário. O critério para aceitar:

| Atualização | O que precisa passar antes do merge |
|---|---|
| Actions, Terraform, imagem base | as verificações do próprio PR |
| Front | as verificações e `npm run build` local: o CI não compila o front, só a Vercel no preview |
| API | as verificações e a corrida do k6 contra a imagem do PR, pelo motivo acima |

Merge na `main` que toque a API ou os workflows dispara o deploy, com varredura do Trivy e rollback automático se a versão nova não responder.

### Front, com Playwright

```bash
docker compose up -d          # banco, API e front semeados
cd web
npm run e2e                   # 27 testes, em computador e celular
npm run e2e:ui                # o mesmo, com navegador visível e passo a passo
```

Rodam contra a pilha do Compose, e não contra dublês de API: o teste exercita o mesmo artefato que o avaliador abre, pela mesma razão que a verificação da API é sempre por HTTP contra o servidor de verdade.

Os seletores são os que a pessoa vê: papel e nome acessível, nunca classe de CSS. Um teste que procura `.btn-primary` passa com o botão invisível; um que procura o botão chamado *Reservar* falha quando o rótulo some, que é o defeito que importa. De quebra, escrever assim obriga a interface a ter nomes acessíveis.

Cada teste roda duas vezes, em **computador e em celular**. Não é redundância: o mapa vazando pela lateral, a barra fixa de ação e o rótulo da trilha só existem como problema em uma das duas larguras. Quatro casos são exclusivos do celular, um é exclusivo do computador, e o restante vale nos dois.

A sessão é autenticada uma vez por papel e reaproveitada. Sem isso a suíte estoura o **limitador de tentativas da própria API** (D8) e passa a falhar com 429, no teste seguinte e não no que gastou as tentativas. O formulário de login continua coberto pelo caso que verifica se a seleção de poltronas sobrevive a ele.

Um trabalhador só, de propósito: os testes compram poltronas num banco compartilhado, e dois em paralelo disputariam o mesmo assento. A recusa por disputa é o sistema funcionando, e faria o teste falhar por um motivo que não é o dele.

---

## Chave do TMDb

Só é necessária para **rodar localmente** e afeta apenas a busca de filmes pelo organizador. Todo o resto do fluxo funciona sem ela: os dados do filme são copiados para a tabela `events` no momento da publicação, e o seed tem uma ficha embutida de reserva caso a API do TMDb não responda.

Obtenha em [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api). É gratuita e sai na hora. Use a **API Key (v3 auth)**, a chave curta.

---

## Limitações conhecidas

Declaradas porque existem, não porque passaram despercebidas.

**Enumeração de usuários no cadastro.** Ao tentar criar conta com um e-mail já usado, a resposta confirma que a conta existe. Esconder isso exigiria confirmação por e-mail, listado como fora de escopo. Sem esse canal, esconder trocaria o vazamento por um usuário travado sem entender por que o cadastro não conclui. A exposição é compensada por limite de tentativas por IP e por conta. Registrado em `docs/DECISOES.md` como D8.

**O limitador de tentativas vive em memória.** A contagem zera quando o processo reinicia. Persistir em banco custaria uma escrita por tentativa de login, o que transformaria o próprio limitador em vetor de esgotamento de disco. É mitigação de custo, não bloqueio absoluto.

**O cache do TMDb também é em memória**, com prazo de seis horas e teto de 200 entradas. Some quando o processo reinicia, e isso é aceitável: o catálogo do cliente não depende dele.

**Não há recuperação de senha**, nem envio de e-mail, nem nota fiscal, nem revenda entre usuários, todos fora de escopo pelo enunciado.

**Uma instância só.** Sem Load Balancer nem segunda máquina, o deploy troca o contêiner no lugar e há alguns segundos sem resposta, e uma falha da EC2 tira a API do ar até a recuperação automática da AWS. O rollback automático encurta a queda causada por versão ruim, mas não a evita. Duas instâncias atrás de um balanceador resolveriam, por mais que o dobro do custo atual (D38).

**Sem proteção contra ataque de volume distribuído.** O teto por IP e a fila de requisições seguram abuso de uma origem ou de poucas; milhares de IPs ao mesmo tempo derrubariam a API. A resposta prevista é fechar o site por uma variável do Terraform, e não um WAF, que custaria mais que a aplicação inteira (D40).

**Backup do banco de um dia.** É o máximo que o plano gratuito da conta permite no RDS. A restauração cobre qualquer minuto das últimas 24 horas; um erro percebido depois disso não tem volta. A restauração foi testada, não presumida: RPO de 252 segundos e RTO de 8 minutos, com os dados criados minutos antes presentes no banco restaurado (`docs/deploy-aws.md`).

**O endereço depende do sslip.io.** O domínio da API é o próprio IP escrito como nome, resolvido por um DNS de terceiro. Se o serviço sair do ar, a API fica inalcançável mesmo funcionando. Um domínio próprio elimina a dependência.

**Rollback não desfaz migration.** Voltar para uma imagem anterior a uma mudança de schema exige `alembic downgrade` manual antes (`docs/deploy-aws.md`).

**Cinemas não têm dono.** Qualquer organizador cadastra, edita e remove cinema, sala e funcionário, inclusive de outro organizador. Eventos e sessões são protegidos por dono, o cadastro de locais não. É o que impede abrir o cadastro de organizador ao público, como fazem Sympla e Eventbrite: sem cercar o local primeiro, o catálogo ficaria à mercê de quem aparecesse. O caminho é dar `organizer_id` ao `Venue`, e não foi percorrido por escopo (D22).

**A lista de municípios depende do IBGE.** Se a API de localidades estiver fora, não dá para cadastrar cinema novo, e nada mais que isso: catálogo, compra e portaria não passam por lá. A resposta nesse caso diz o que aconteceu, e o seed traz os códigos escritos para semear sem internet (D23).

**Só há mapa de assentos.** O desafio pede um dos dois modos, e a escolha foi assento numerado por ser onde a garantia de unicidade aparece de verdade.

**O mapa não atualiza sozinho.** Ele mostra a ocupação do momento em que a tela abriu. Se outra pessoa comprar a poltrona enquanto você escolhe, o mapa continua mostrando livre até você recarregar. Atualizar em tempo real exigiria websocket ou consulta periódica, e nenhum dos dois muda a garantia: quem tentar reservar uma poltrona já vendida recebe recusa explícita, com o nome da poltrona perdida. A garantia vive no índice único do banco, não no que a tela está mostrando. O custo de um mapa desatualizado é no máximo uma escolha refeita, nunca uma venda dupla.

---

## Documentação do projeto

| Arquivo | O que responde |
|---|---|
| `docs/ESPECIFICACAO.md` | O que o sistema faz e quando está pronto |
| `docs/DECISOES.md` | Por que faz assim, e o que foi descartado, em 40 decisões |
| `docs/deploy-aws.md` | Arquitetura na AWS, custo, deploy, rollback e como apagar tudo |
| `CLAUDE.md` | Contexto que restringe o agente de IA: garantias, tokens visuais, convenções |
| `AI-USAGE.md` | Como a IA foi conduzida e onde a saída dela foi corrigida |
| `Prototipos/` | Protótipo da sala de cinema desenhado antes da tela existir |

---

## Identidade visual

Direção **recibo térmico**: papel creme, tipografia monoespaçada, alinhamentos de cupom fiscal, tracejado como divisor. Seis cores no total.

A escolha não é estética por si só: o objeto que o sistema produz **é um bilhete**, e a interface adota a linguagem do próprio objeto. O ingresso na tela tem picote com recorte, corpo e canhoto.

Uma regra sustenta a paleta. O carmim `#A32B1C` é **reservado** a ação e atenção: poltrona selecionada, erro, recusa. Se aparecer como decoração, está errado.

Os cinco estados de assento se distinguem por **forma e textura além de cor**: livre é contorno, ocupada é preenchida, em espera é hachurada, a sua tem marca de conferido, e acessível é círculo com o símbolo internacional. Tirando a cor da tela, o mapa continua utilizável, porque o par carmim/bege é indistinguível para parte das pessoas.

A única exceção ao monoespaçado é a sinopse vinda do TMDb, em fonte proporcional. Mono alinha dado tabular sozinho e perde em prosa corrida; a sinopse é o único texto longo do sistema.
