# Uso de IA

## Agente de IA

Claude Code (Opus 5), em sessão contínua conduzida por prompt no terminal.

## Como o projeto foi conduzido

O enunciado não foi colado no agente de IA pedindo o sistema pronto. A ordem foi outra:

**1. Estratégia antes de código.** A primeira tarefa foi analisar o desafio e propor o que priorizar — não implementar. Saiu um plano de sete dias com uma regra de corte: o fluxo completo roda antes de qualquer polimento.

**2. Decisões de produto tomadas por mim.** Stack, escopo de reserva, direção visual e nome do produto. Numa delas — a personalidade tipográfica — escolhi contra a recomendação do agente.

**3. Identidade visual travada antes da primeira tela.** Três direções foram prototipadas lado a lado e comparadas. A escolhida virou tokens no `CLAUDE.md` antes de qualquer componente existir, para não construir algo genérico e reestilizar depois.

**4. Explicação exigida a cada bloco.** Nada foi aceito sem eu entender o porquê. Onde a explicação não se sustentou, o código mudou — os casos estão listados abaixo.

## Artefatos de condução

| Arquivo | Função |
|---|---|
| `CLAUDE.md` | Restringe o agente: garantias inegociáveis, tokens visuais, convenções |
| `docs/ESPECIFICACAO.md` | O que o sistema faz e quando está pronto |
| `docs/DECISOES.md` | Por que faz assim, e o que foi descartado |

O `CLAUDE.md` é o que impede o agente de reintroduzir soluções já rejeitadas — por exemplo, trocar a constraint do banco por uma verificação em Python.

## Mudanças que partiram de mim

**Monoespaçado mantido no sistema inteiro.**
O agente desaconselhou tipografia monoespaçada no painel do organizador, alegando cansaço visual. Escolhi a direção mesmo assim. Quando o argumento foi detalhado, a objeção não se sustentava: mono alinha dado tabular melhor que proporcional, e o painel é exatamente isso. O ponto fraco real do mono é prosa corrida — a sinopse do TMDb, e só ela, ficou em fonte proporcional.

**Sala virou tabela própria.**
O modelo trazia sala e dimensões como campos soltos em `Showing`. Ao revisar linha a linha, questionei por que sala não era entidade. O agente argumentou contra, por escopo. Mantive o questionamento, e ao destrinchar o modelo ficou claro que `rows` e `seats_per_row` viravam dado morto depois que os assentos eram gerados — e passariam a mentir sobre a tabela `seats` se fossem editados. Virou a decisão D6.

**Cinema virou tabela própria.**
O agente havia argumentado que o cinema não merecia entidade por não ter atributos além do nome. Pedi que reconsiderasse pensando em como isso seria feito num sistema real. O argumento caiu: a busca que estrutura qualquer plataforma de ingresso é por cidade e cinema, e sem campo de cidade ela é impossível. Virou a decisão D7, que reverte a D6 nesse ponto.

**Enumeração de usuários no cadastro.**
Ao revisar as rotas de autenticação, perguntei se responder "já existe uma conta com este e-mail" não era falha de segurança. Era. E o agente havia tomado o cuidado oposto no login, onde senha errada e e-mail inexistente retornam a mesma resposta — a inconsistência passou despercebida. Fechar de verdade exige confirmação por e-mail, que está fora do escopo. Pedi que a exposição fosse documentada com o motivo e compensada por limite de tentativas. Virou a decisão D8 e o módulo `app/ratelimit.py`.

**Argumento falso sobre o cache do TMDb derrubado.**
O agente recomendou cache em tabela alegando que, sem ele, o catálogo sairia do ar caso o TMDb caísse. Perguntei por que reiniciar o processo seria um problema. A justificativa não se sustentava: o catálogo do cliente lê da nossa tabela `events`, porque os dados do filme são copiados na publicação — o TMDb só é consultado enquanto o organizador procura o filme. Ficou cache em memória, proporcional ao uso real.

**Prazo de validade do cache recalculado.**
Perguntei se o cache precisava de tempo de vida. O agente implementou 30 minutos, e questionei se aquilo ajudava em alguma coisa — o organizador buscaria, e meia hora depois a entrada teria sido descartada à toa. A objeção procedia, e expôs uma confusão na justificativa: quem limita memória é o teto de entradas, não o prazo. O prazo serve só contra dado velho, e sinopse e pôster de filme lançado praticamente não mudam. Subiu para seis horas, que atravessam uma jornada do organizador sem expirar nada.

**Troca de sala checada antes de virar regra.**
O agente levantou o caso de trocar a sala de uma sessão já vendida e ofereceu três tratamentos. Antes de escolher, pedi que verificasse se aquilo acontece de verdade num cinema — não queria regra construída sobre hipótese. Acontece: projetor quebra, sessão vende mal e migra para sala menor, sessão esgota e é promovida. A verificação também corrigiu a descrição do problema, que estava errada: os assentos não ficariam órfãos, já que pertencem à exibição e não à sala. O que quebra é a correspondência com a sala física. Virou a decisão D9.

**Hibernação do plano gratuito tratada em vez de aceita.**
O agente apresentou o arranque a frio do Render como desvantagem fixa: dezenas de segundos na primeira requisição depois de inatividade. Perguntei se não daria para manter o serviço acordado por chamadas periódicas, ou disparar o religamento assim que alguém abre o site, antes de clicar em qualquer coisa. As duas coisas funcionam e resolvem partes diferentes. Ficaram três camadas: aquecimento do `/health` quando a página monta, ping agendado em horário comercial, e aviso honesto na interface quando ainda assim houver espera. Isso desempatou a escolha da plataforma a favor do Render, onde o limitador de tentativas e o cache funcionam de verdade — numa função serverless os dois perderiam o efeito.

**Mapa de assentos revisado até virar o que eu queria.**
Devolvi a primeira versão da tela com dez apontamentos: mapa pequeno demais, poltrona ocupada em cinza claro demais para ser notada, tela do cinema fina e no lugar errado, símbolo de acessibilidade ausente, dados da sessão em corpo pequeno demais para conferir antes de comprar, ausência de pôster e falta de numeração nas colunas. Duas mudanças alcançaram o back-end: pedir a tela do cinema embaixo obrigou a inverter a ordem das fileiras, para a fileira A encostar nela em vez de ficar no fundo da sala; e mover as poltronas acessíveis para a fileira A mudou a geração do mapa em `seating.py`.


## Ajustes surgidos na verificação

**`passlib` e `python-jose` trocados por `bcrypt` e `PyJWT`.**
A lista inicial de dependências usava as duas primeiras. Um teste de instalação revelou que `passlib 1.7.4` quebra com `bcrypt 5.x` — lê um atributo interno removido na versão 4.1. As bibliotecas diretas resolvem o problema e ainda eliminam duas dependências.

**Ambiente corrigido antes da primeira linha.**
O Python instalado era 32-bit numa máquina 64-bit. Pacotes como `psycopg` e `pydantic-core` não distribuem versão compilada para essa combinação, e a instalação falharia tentando compilar do zero. Detectado antes de escrever código.

**Migrations revisadas antes de aplicar.**
O `--autogenerate` do Alembic nomeou uma chave estrangeira como `None`, o que quebraria o `downgrade`. Corrigido à mão nas duas migrations em que ocorreu.

**Limite de tentativas recalibrado.**
O primeiro valor era 10 logins por IP a cada 5 minutos. Os testes começaram a falhar por esbarrar nele — que é exatamente o que aconteceria com usuários reais atrás de um IP compartilhado de escritório ou operadora móvel. O limite por IP subiu para 60; a defesa contra força bruta ficou na janela por conta, que independe de origem.

## O que foi feito sem IA

A escolha da stack, do escopo de reserva, da direção visual e do nome do produto. A decisão de usar TMDb com mapa de assentos em vez de pista por quantidade. E a leitura crítica de cada explicação antes de aceitar o código — de onde saíram as mudanças listadas acima.

---

*Atualizado ao longo do desenvolvimento.*
