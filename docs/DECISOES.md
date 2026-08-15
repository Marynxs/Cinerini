# Registro de decisões

Ordem cronológica. Cada entrada registra o que foi decidido, o que foi descartado e por quê.

---

## D1 · Catálogo externo: TMDb em vez de Ticketmaster

**Decidido:** TMDb como fonte do catálogo, modelando o domínio como cinema.

**Descartado:** Ticketmaster Discovery. A API é mais rica em dados reais de local, mas o fluxo que ela sugere — shows com pista e setores — se resolve por quantidade de ingressos, não por assento.

**Por quê:** o requisito de assento único é a garantia técnica mais interessante do desafio, e ela só aparece de verdade num mapa de assentos. Cinema também dá uma cadeia coerente: filme em cartaz → sessão → poltrona. O TMDb ainda fornece pôster e backdrop, o que resolve boa parte da carga visual sem produção de imagem.

---

## D2 · Identidade visual: recibo térmico sobre papel

**Decidido:** paleta de papel creme, tipografia monoespaçada (IBM Plex Mono), alinhamentos de cupom fiscal, tracejado como divisor. Seis cores no total.

**Descartado:** duas direções alternativas — uma escura com âmbar de marquise, outra editorial em branco com grid suíço.

**Por quê:** o objeto que o sistema produz é um bilhete, e a interface adota a linguagem do próprio objeto. A escolha também é uma resposta ao critério declarado no enunciado: uma paleta de papel não é o que uma ferramenta generativa produz por padrão, e a coerência entre o meio e o produto sustenta a decisão além do gosto pessoal.

**Regra que decorre daí:** o carmim `#A32B1C` é reservado a ação e atenção — assento selecionado, erro, recusa. Nunca decoração.

---

## D3 · Monoespaçado com uma exceção

**Decidido:** todo o sistema em IBM Plex Mono, exceto a sinopse vinda do TMDb, que usa IBM Plex Sans.

**Por quê:** monoespaçado alinha dado tabular sozinho — o painel do organizador, os totais do checkout e os códigos de ingresso ganham com isso. Prosa corrida é o caso em que ele perde: a sinopse é o único texto longo do sistema, e forçá-la em mono cobraria legibilidade sem devolver nada. A fonte irmã preserva a coerência do conjunto.

---

## D4 · Estados de assento distinguíveis sem cor

**Decidido:** os cinco estados (livre, seu, ocupado, em espera, acessível) se diferenciam por forma e textura além de cor — contorno, preenchimento, hachura e círculo.

**Por quê:** o par crítico do mapa é carmim sobre bege, indistinguível para parte dos usuários com deficiência de visão de cores. Redundância de codificação resolve isso sem custo de implementação.

---

## D5 · Front sem framework de servidor

**Decidido:** React com Vite.

**Descartado:** Next.js.

**Por quê:** o back-end é o FastAPI. As funcionalidades que justificam o Next — renderização no servidor e rotas de API próprias — ou não têm uso aqui ou duplicariam responsabilidade que já vive na API. Vite entrega o mesmo resultado com menos superfície.

---

## D6 · Sala como entidade própria

**Decidido:** `Room` vira tabela, com `venue`, `name` e o layout (`rows`, `seats_per_row`). `Showing` passa a apontar para uma sala em vez de repetir esses dados; `venue` sai de `Event`.

**Descartado:** manter sala e layout como campos soltos em `Showing`, que era o modelo inicial.

**Por quê:** o layout é propriedade física da sala, não da exibição — "Sala 3" tem 8×12 lugares independente de qual filme passa nela. No modelo anterior, `rows` e `seats_per_row` viravam dado morto assim que os assentos eram gerados, e passariam a mentir sobre o conteúdo real de `seats` se alguém os editasse depois. Agora o layout é cadastrado uma vez e toda exibição naquela sala herda a mesma geometria.

`venue` migrou de `Event` para `Room` no mesmo movimento: normalizar a sala mantendo o local como texto solto no evento deixaria ambíguo a que cinema uma "Sala 3" pertence.

**Até onde a normalização vai:** revisto em D7.

---

## D7 · Cinema como entidade própria

**Decidido:** `Venue` vira tabela com `name`, `city`, `state` e `address`. `Room` aponta para ela em vez de guardar o nome do cinema como texto.

**Descartado:** manter o cinema como texto em `Room`, que era a posição adotada em D6.

**Por quê:** o argumento de D6 — "o cinema não tem atributo além do nome" — estava errado, e a evidência é o filtro. A busca que estrutura toda plataforma de ingresso é por **cidade e cinema**, não por título. Com o local como texto não existia campo de cidade, então filtrar por região era impossível, e listar cinemas dependeria de `SELECT DISTINCT venue`, frágil a qualquer divergência de digitação: "Cinemark Eldorado" e "cinemark eldorado" virariam dois cinemas.

A cidade é indexada porque é o primeiro filtro que o cliente aplica, antes mesmo de escolher filme.

**Até onde a normalização vai agora:** fora ficaram coordenadas geográficas, fuso horário, telefone e horário de funcionamento. Todos existem em sistemas reais — o fuso, em particular, é obrigatório em rede nacional, já que o Brasil tem quatro e uma sessão gravada em UTC precisa ser exibida no horário local de cada cinema. Nenhum deles entra aqui porque **nenhuma tela do projeto os leria**, e campo que nada consome ainda custa seed, formulário e manutenção.

O critério que separa D6 de D7 é esse: não "isso é mais normalizado?", e sim "existe tela que consome esse campo?".

---

## D8 · Cadastro revela e-mail já cadastrado, com limite de tentativas

**Decidido:** o cadastro responde `409` explicitamente quando o e-mail já tem conta. A exposição é compensada por limite de tentativas por IP e por conta.

**Descartado:** responder sempre sucesso e informar o resultado real por e-mail.

**Por quê:** a alternativa descartada é a solução correta — quem já tem conta recebe um aviso, quem não tem recebe o link de confirmação, e nada vaza para quem só está sondando. Mas ela depende de envio de e-mail, listado como fora de escopo no enunciado. Sem esse canal, esconder a informação apenas trocaria o vazamento por um usuário travado sem entender por que o cadastro não conclui.

**O que isso expõe:** enumeração de usuários. Quem tiver uma lista de e-mails descobre quais têm conta tentando cadastrar cada um. É a mesma informação que o login se recusa deliberadamente a entregar — ali senha errada e e-mail inexistente retornam resposta idêntica — e admitir a inconsistência é mais honesto do que fingir que o cuidado no login basta.

**Mitigação implementada:** duas janelas deslizantes independentes.

| Janela | Limite | Defende de |
|---|---|---|
| Cadastro por IP | 20 / hora | Varredura de lista de e-mails |
| Login por IP | 60 / 5 min | Volume anormal de rede |
| Login por conta | 8 / 15 min | Força bruta de senha |

Os limites por IP são folgados de propósito: escritório, universidade e operadora móvel colocam muita gente atrás de um endereço só, e apertar ali puniria usuário legítimo sem impedir quem distribui o ataque entre vários endereços. A defesa efetiva contra força bruta é a janela **por conta**, que independe de origem. Acerto de senha zera a contagem, para que erro de digitação não bloqueie o dono.

**Limitação conhecida:** a contagem vive em memória e zera quando o processo reinicia — no Render, que hiberna por inatividade, isso ocorre. Persistir em banco custaria uma escrita por tentativa, o que transformaria o próprio limitador em vetor de esgotamento de disco. É mitigação de custo, não bloqueio absoluto, e fica declarada como tal no README.

---

## D9 · Sala travada depois da primeira venda

**Decidido:** a sala de uma exibição pode ser trocada enquanto não houver ingresso. Sem venda, o mapa é descartado e refeito no layout da sala nova. Com venda, a troca é recusada.

**Descartado:** travar a sala já na publicação, e permitir a troca com remapeamento dos ingressos vendidos.

**Por quê:** trocar de sala é operação real de cinema — projetor quebra, sessão vende mal e migra para uma sala menor, sessão esgota e é promovida para uma maior. Ignorar o caso deixaria o organizador sem saída legítima.

O que a troca quebra não é integridade referencial: `Seat` pertence à exibição, não à sala, então nenhum assento fica órfão. O que quebra é a correspondência com a sala física — a exibição passaria a anunciar "Sala 5" exibindo um mapa gerado a partir do layout da Sala 3, e o cliente compraria a F7 de uma sala que pode não ter fileira F.

Travar já na publicação seria mais simples, mas custaria o caso mais comum: publicar, notar a sala errada e corrigir antes de vender. O remapeamento dos ingressos é o que uma rede real faria, e exige interface de realocação e política de reembolso — sistema à parte.

**Onde a linha foi traçada:** o gatilho é a primeira venda, não a publicação. Preço, horário e áudio continuam editáveis mesmo com ingresso vendido: quem comprou pagou o valor registrado no pedido, e promoção é operação corriqueira.

---

## D10 · Sessão cancelada permanece visível, com motivo

**Decidido:** cancelar uma sessão não a remove. Ela ganha estado próprio e um campo de motivo em texto livre, exibido a quem tem ingresso: *"Sessão cancelada: problema no projetor."* Os ingressos passam a `cancelled` e os pedidos registram o reembolso simulado.

**Descartado:** remover a sessão do sistema, e cancelá-la silenciosamente sem justificativa.

**Por quê:** remover deixaria o ingresso do cliente desaparecer sem explicação — ele abriria "Meus ingressos" e encontraria um vazio, sem saber se perdeu o acesso, se foi golpe ou se o evento mudou. Cancelar sem motivo é pouco melhor: informa que algo aconteceu e esconde o quê.

O motivo em texto livre existe porque a causa é operacional e imprevisível — falha de equipamento, público mínimo não atingido, interdição da sala. Uma lista fechada de opções não cobriria os casos reais e obrigaria a escolher "outro" com frequência.

**Efeito colateral já resolvido:** liberar os assentos não exige código. O índice único é parcial em `status <> 'cancelled'`, então o ingresso cancelado sai do índice e a poltrona volta ao estoque sozinha — a escolha de índice parcial, feita na modelagem inicial, pagando aqui.

**Pendente de implementação.** Depende do fluxo de compra existir para ter o que cancelar. Entra junto com ele.

**Beco sem saída que motivou a decisão:** a D9 recusa a troca de sala orientando "cancele a sessão e crie outra", mas remover sessão com ingresso também é recusado. Sem D10, o organizador com sala interditada e ingressos vendidos não tem saída nenhuma.

---

## D11 · Regra de negócio em módulos, não em classes de serviço

**Decidido:** vira classe o que guarda algo entre chamadas; vira função de módulo o que só transforma entrada em saída. A regra de negócio fica em arquivos próprios — `seating.py`, `security.py`, `tmdb.py` — e não dentro das rotas.

**Descartado:** classes de serviço agrupando funções, e uma camada de acesso a dados por cima do SQLAlchemy.

**Por quê:** classe que não guarda nada não protege nada — em Python o próprio arquivo já agrupa funções, ao contrário de linguagens onde toda função precisa morar numa classe. E envolver o SQLAlchemy numa camada de acesso repetiria o que ele já entrega: a `Session` é exatamente essa camada, e a classe extra só encaminharia chamadas.

Onde há estado, a classe está lá: `TTLCache` e `SlidingWindow` guardam dados entre chamadas e as regras que os governam.

**Consequência:** o fluxo de reserva encadeia verificação de disponibilidade, trava com prazo, pagamento e emissão do ingresso. Isso não cabe dentro de uma rota, e vai para módulo próprio — por tamanho, não por paradigma.

---

## D12 · Sessão é recurso de primeiro nível

**Decidido:** operações sobre uma sessão específica ficam em `/showings/{id}`. Criar e listar sessões de um evento continuam em `/events/{id}/showings`.

**Descartado:** manter tudo aninhado sob `/events/`, como estava.

**Por quê:** as rotas de detalhe, edição, remoção e mapa de assentos não usam o `event_id` — ele aparecia na URL sem participar da resolução. Aninhamento que não identifica nada é ruído, e obrigaria o front a carregar o evento só para montar o endereço da sessão.

A convenção adotada é a usual: coleção sob o pai, item na raiz.

**Momento da mudança:** feita antes de o front existir. Depois do dia 4 custaria alterar os dois lados ao mesmo tempo.
