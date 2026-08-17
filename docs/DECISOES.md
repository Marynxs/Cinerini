# Registro de decisões

Ordem cronológica. Cada entrada registra o que foi decidido, o que foi descartado e por quê.

Não há D13: foi um erro de contagem ao numerar o D14, não uma decisão removida. O número fica vago de propósito. Renumerar as seguintes faria quatro mensagens de commit já publicadas apontarem para a decisão errada — e o histórico do Git não se reescreve para consertar uma sequência.

---

## D1 · Catálogo externo: TMDb em vez de Ticketmaster

**Decidido:** TMDb como fonte do catálogo, modelando o domínio como cinema.

**Descartado:** Ticketmaster Discovery. A API é mais rica em dados reais de local, mas o fluxo que ela sugere — shows com pista e setores — se resolve por quantidade de ingressos, não por assento.

**Por quê:** o requisito de assento único é a garantia técnica mais interessante do desafio, e ela só aparece de verdade num mapa de assentos. Cinema também dá uma cadeia coerente: filme em cartaz → sessão → poltrona. O TMDb ainda fornece pôster e backdrop, o que resolve boa parte da carga visual sem produção de imagem.

---

## D2 · Identidade visual: recibo térmico sobre papel

**Decidido:** paleta de papel creme, tipografia monoespaçada (IBM Plex Mono), alinhamentos de cupom fiscal, tracejado como divisor. Seis cores no total.

**Descartado:** duas direções alternativas — uma escura com âmbar de marquise, outra editorial em branco com grid suíço.

**Por quê:** papel, monoespaçado e picote remetem ao bilhete de cinema antigo — o canhoto que se destacava na entrada. É o ar de cinema que o produto precisava ter, e nenhuma das outras duas direções entregava: escuro com âmbar puxa para aplicativo de streaming, e o editorial em branco puxa para revista.

O objeto que o sistema produz é um bilhete, então a interface adota a linguagem do próprio objeto. Essa coerência entre meio e produto é o que sustenta a decisão além do gosto pessoal.

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

---

## D14 · Recusa de pagamento não devolve a poltrona

**Decidido:** cartão recusado mantém as poltronas reservadas até o prazo de dez minutos vencer. O pedido fica em estado recusado, mas continua pagável.

**Descartado:** cancelar os ingressos e liberar as poltronas no instante da recusa, que era o comportamento anterior.

**Por quê:** a justificativa original — "segurar a poltrona puniria outros clientes por uma compra que não vai acontecer" — não se sustenta. A reserva já tem prazo, então as poltronas nunca ficariam presas indefinidamente; e cartão negado quase sempre significa que a pessoa vai tentar outro, não que desistiu.

Do jeito anterior, a tela oferecia "tentar outro cartão" e o pedido já estava encerrado: qualquer nova tentativa falhava, e a escolha de poltronas se perdia por causa de um dígito errado. Nenhum checkout real se comporta assim.

**O prazo continua valendo:** recusa não estende a reserva. Pagar depois do vencimento é recusado, e os assentos voltam ao estoque pela liberação sob demanda.

---

## D15 · Uma reserva aberta por cliente e sessão

**Decidido:** criar uma reserva cancela a reserva aberta que o mesmo cliente já tivesse naquela sessão, devolvendo as poltronas anteriores ao estoque na hora.

**Descartado:** deixar as duas reservas coexistirem até a mais antiga vencer.

**Por quê:** o cliente que volta ao mapa para trocar de poltrona não está iniciando uma segunda compra — está corrigindo a primeira. Sem a substituição, as poltronas abandonadas ficariam retidas por dez minutos sem que ninguém as quisesse, e o cliente apareceria com dois pedidos abertos da mesma sessão, sem saber qual pagar.

**A regra é por sessão, não por cliente:** quem está comprando ingressos de dois filmes ao mesmo tempo mantém as duas reservas.

**Consequência na interface:** as poltronas da reserva aberta voltam ao mapa já selecionadas e editáveis, em vez de bloqueadas. Marcá-las como ocupadas faria o cliente pensar que perdeu a própria escolha.

---

## D16 · Ingresso cancelado sai da lista em dois prazos diferentes

**Decidido:** o ingresso cancelado deixa de aparecer em "Meus ingressos" depois de um prazo que depende de quem cancelou — trinta minutos quando foi o próprio cliente, até o horário da sessão quando foi o cinema. A linha nunca é apagada do banco.

**Descartado:** um prazo único para os dois casos, e sumir no instante do cancelamento.

**Por quê:** os dois cancelamentos têm leitores diferentes. Quem cancelou o próprio ingresso já sabe o motivo, e o único papel da janela é não fazer o bilhete evaporar no mesmo clique — desaparecimento instantâneo se lê como erro, não como confirmação. Quem teve a sessão cancelada pelo cinema precisa do oposto: a explicação tem de estar lá justamente perto da data em que iria, que é quando vai procurar. Um prazo só serviria mal aos dois.

**Filtro na consulta, nunca `DELETE`:** o ingresso é registro de uma compra que existiu, e o índice parcial de D1 depende do status da linha. Apagá-la trocaria uma lista limpa por um histórico falsificado.

**Custo:** a coluna `tickets.cancelled_at` passou a existir para que haja de onde contar o prazo — `status` sozinho não diz quando mudou. É o par de `used_at`, que existe pela mesma razão.

---

## D17 · Portaria: cinco estados, e o evento conferido antes do estado

**Decidido:** `POST /gate/validations` responde sempre 200 com um estado no corpo — `valid`, `invalid`, `already_used`, `wrong_event` ou `cancelled`. O evento é conferido antes do estado do ingresso, e a marcação de uso é a própria escrita condicional.

**Descartado:** traduzir os desfechos em códigos HTTP — 404 para inexistente, 409 para já utilizado. E resolver o estado com um `SELECT` antes do `UPDATE`.

**Por quê o corpo e não o status:** os desfechos têm o mesmo posto. Quem lê é um operador com uma pessoa parada na frente, e um ingresso recusado é resposta, não falha de requisição. Espalhá-los por códigos faria a tela tratar metade dos casos no caminho de erro do cliente HTTP, onde não há corpo padronizado para carregar a poltrona, o nome ou o horário da entrada anterior.

**Por quê o evento antes do estado:** descobrir tarde que o ingresso é da sala ao lado já teria consumido um ingresso legítimo de outra portaria. Verificado: o ingresso recusado por `wrong_event` continua `valid` no banco.

**Quinto estado:** um ingresso reembolsado apresentado na porta é situação real, e chamá-lo de "inválido" faria o operador tratar como fraudador quem apenas cancelou e esqueceu. É a mesma razão que separa `wrong_event` de `invalid` — a diferença entre "não deixe entrar" e "não deixe entrar aqui".

**Digitação manual:** o operador digita o `jti` quando a câmera falha, e aí não há assinatura para conferir. O que sustenta esse caminho é o `jti` ser um uuid4 — 122 bits que não se adivinham — somado ao papel de portaria exigido na rota. É um controle diferente do da garantia 2, não uma brecha nela: sem credencial de portaria o código digitado não vale nada.

---

## D18 · Deploy em três serviços, com o banco fora do Render

**Decidido:** API no Render, front na Vercel, banco no Neon. A infraestrutura da API fica em `render.yaml`, versionada.

**Descartado:** o Postgres gratuito do próprio Render, que reuniria banco e API num painel só. E função serverless para a API.

**Por quê o banco fora:** o Postgres gratuito do Render expira em 30 dias. O sistema morreria sozinho depois da avaliação, e a primeira coisa que quem abrisse o link veria seria um erro de conexão. O Neon não expira.

**Por quê não serverless:** o limitador de tentativas e o cache do TMDb vivem em memória. Numa função que sobe e morre a cada requisição, os dois perderiam o efeito — o limitador zeraria a contagem a cada tentativa, que é exatamente o que ele existe para impedir. Um processo de vida longa é requisito, não preferência.

**Hibernação tratada em três camadas**, porque nenhuma resolve sozinha: o front chama `/health` ao montar e gasta o religamento enquanto a pessoa lê a tela; um agendamento do GitHub Actions mantém o serviço acordado das 8h às 23h, cobrindo o primeiro visitante do dia; e a tela de carregamento explica a espera depois de quatro segundos. As duas primeiras encurtam a espera, a terceira trata a que sobrar — dizer o motivo é o que separa "está lento" de "está quebrado".

**Migration no build e não no pre-deploy:** comando de pré-deploy exige instância paga. Com uma instância só e sem exigência de janela sem downtime, aplicar no build basta e mantém `alembic upgrade head` como o único caminho de mudança de schema.

---

## D19 · Credenciais de teste visíveis no ambiente publicado

**Decidido:** o painel de contas semeadas aparece também em produção, sob o rótulo "ambiente de demonstração", com a senha escrita ao lado.

**Descartado:** prendê-lo ao ambiente local, que era o comportamento anterior.

**Por quê:** as mesmas credenciais estão no README de um repositório público. Escondê-las na tela não removia a informação de lugar nenhum — era teatro de segurança, a aparência do cuidado sem o efeito. E cobrava caro justamente onde não se deve: os primeiros trinta segundos de quem abre o link são o momento mais valioso do projeto, e gastá-los procurando credenciais em outra aba é atrito no único caminho que importa.

**O que a decisão aceita:** vandalismo. Quem entrar como organizador pode cancelar sessões e deixar a demonstração quebrada. O risco já existia — o README entrega as credenciais de qualquer forma — e o estrago se desfaz com `python -m app.seed --reset`. O que muda é a facilidade, e ela é aceita porque o custo do dano é um minuto e o custo do atrito é a primeira impressão.

**O rótulo é parte da decisão:** dizer "ambiente de demonstração" na interface declara a natureza do que está no ar. Esconder as contas fingindo que aquilo é produção seria a postura menos honesta das duas.

---

## D20 · Catálogo mantém a tela anterior enquanto atualiza

**Decidido:** ao voltar ao catálogo, a última resposta daquela cidade continua na tela enquanto a nova requisição acontece. A busca ocorre sempre.

**Descartado:** cache com prazo de validade, e o comportamento anterior de apagar a tela antes de buscar.

**Por quê não o cache:** a resposta do catálogo carrega `seats_available`, que é o que marca a sessão como esgotada. Guardá-la por alguns minutos faria o cliente clicar numa sessão que já lotou. Não seria catastrófico — o mapa é a fonte de verdade e a reserva perdida devolve a recusa clara de D1 — mas trocaria um incômodo visual por informação errada, e informação errada é pior que espera.

**Por quê não apagar a tela:** o `setFilmes(null)` anterior era o que fazia o catálogo piscar em branco a cada volta. Não era falta de cache; era a tela se apagando antes de ter o que colocar no lugar. Com a API hibernando no plano gratuito, isso vira meio minuto de tela vazia sobre conteúdo que já estava pronto.

**Consequência no erro:** uma atualização que falha com catálogo na tela não troca o conteúdo por um aviso. O aviso só aparece quando não há nada a mostrar — trocar dado útil por mensagem de erro puniria quem já tinha o que precisava.
