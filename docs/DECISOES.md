# Registro de decisões

Ordem cronológica. Cada entrada registra o que foi decidido, o que foi descartado e por quê.

---

## Índice

O corpo segue ordem cronológica; o índice agrupa por assunto.

**Produto e identidade**  
[D1](#d1--catálogo-externo-tmdb-em-vez-de-ticketmaster) Catálogo externo: TMDb em vez de Ticketmaster  
[D2](#d2--identidade-visual-recibo-térmico-sobre-papel) Identidade visual: recibo térmico sobre papel  
[D3](#d3--monoespaçado-com-uma-exceção) Monoespaçado com uma exceção  
[D4](#d4--estados-de-assento-distinguíveis-sem-cor) Estados de assento distinguíveis sem cor  
[D5](#d5--front-sem-framework-de-servidor) Front sem framework de servidor  

**Modelagem e domínio**  
[D6](#d6--sala-como-entidade-própria) Sala como entidade própria  
[D7](#d7--cinema-como-entidade-própria) Cinema como entidade própria  
[D9](#d9--sala-travada-depois-da-primeira-venda) Sala travada depois da primeira venda  
[D11](#d11--regra-de-negócio-em-módulos-não-em-classes-de-serviço) Regra de negócio em módulos, não em classes de serviço  
[D12](#d12--sessão-é-recurso-de-primeiro-nível) Sessão é recurso de primeiro nível  
[D23](#d23--cidade-e-uf-escolhidas-em-lista-com-o-código-do-ibge-guardado) Cidade e UF escolhidas em lista, com o código do IBGE guardado  
[D28](#d28--cidade-digitada-à-mão-quando-o-ibge-não-responde) Cidade digitada à mão quando o IBGE não responde  
[D29](#d29--catálogo-único-sem-dono-por-organizador) Catálogo único, sem dono por organizador  
[D30](#d30--um-filme-um-evento-e-rascunho-é-o-único-apagável) Um filme, um evento, e rascunho é o único apagável  
[D36](#d36--apagar-sessão-exige-cancelar-antes-e-o-que-passou-pela-portaria-não-sai) Apagar sessão exige cancelar antes, e o que passou pela portaria não sai  
[D35](#d35--encolher-a-sala-é-recusado-sobre-poltrona-vendida) Encolher a sala é recusado sobre poltrona vendida  

**Compra, ingresso e catálogo**  
[D10](#d10--sessão-cancelada-permanece-visível-com-motivo) Sessão cancelada permanece visível, com motivo  
[D13](#d13--recusa-de-pagamento-não-devolve-a-poltrona) Recusa de pagamento não devolve a poltrona  
[D14](#d14--uma-reserva-aberta-por-cliente-e-sessão) Uma reserva aberta por cliente e sessão  
[D15](#d15--ingresso-cancelado-sai-da-lista-em-dois-prazos-diferentes) Ingresso cancelado sai da lista em dois prazos diferentes  
[D19](#d19--catálogo-mantém-a-tela-anterior-enquanto-atualiza) Catálogo mantém a tela anterior enquanto atualiza  
[D31](#d31--zoom-no-mapa-por-roda-pinça-e-barra) Zoom no mapa por roda, pinça e barra  

**Portaria**  
[D16](#d16--portaria-desfechos-no-corpo-e-o-lugar-conferido-antes-do-estado) Portaria: desfechos no corpo, e o lugar conferido antes do estado  
[D20](#d20--leitura-do-qr-por-biblioteca-não-pela-api-do-navegador) Leitura do QR por biblioteca, não pela API do navegador  
[D21](#d21--portaria-vinculada-à-exibição-não-ao-filme) Portaria vinculada à exibição, não ao filme  
[D24](#d24--portaria-é-posto-funcionário-é-a-conta-e-o-turno-é-dele) Portaria é posto, funcionário é a conta, e o turno é dele  
[D26](#d26--cobertura-por-sessão-não-por-funcionário) Cobertura por sessão, não por funcionário  
[D33](#d33--cobertura-conta-quem-está-na-porta-não-quem-tem-o-cargo) Cobertura conta quem está na porta, não quem tem o cargo  

**Contas e papéis**  
[D8](#d8--cadastro-revela-e-mail-já-cadastrado-com-limite-de-tentativas) Cadastro revela e-mail já cadastrado, com limite de tentativas  
[D18](#d18--credenciais-de-teste-visíveis-no-ambiente-publicado) Credenciais de teste visíveis no ambiente publicado  
[D22](#d22--primeiro-cadastro-vira-organizador-e-organizador-promove-organizador) Primeiro cadastro vira organizador, e organizador promove organizador  
[D25](#d25--cadastro-editável-remoção-só-do-que-está-vazio) Cadastro editável, remoção só do que está vazio  
[D27](#d27--organizador-abre-a-portaria-e-o-papel-se-revoga-sem-apagar-a-conta) Organizador abre a portaria, e o papel se revoga sem apagar a conta  
[D32](#d32--promoção-e-revogação-se-desfazem-uma-à-outra) Promoção e revogação se desfazem uma à outra  

**Infraestrutura**  
[D17](#d17--deploy-em-três-serviços-com-o-banco-fora-do-render) Deploy em três serviços, com o banco fora do Render  
[D37](#d37--ocupação-em-lote-e-o-orçamento-de-idas-ao-banco-virou-teste) Ocupação em lote, e o orçamento de idas ao banco virou teste  
[D34](#d34--compose-sobe-o-sistema-sem-credencial-da-máquina) Compose sobe o sistema sem credencial da máquina  
---

## D1 · Catálogo externo: TMDb em vez de Ticketmaster

**Decidido:** TMDb como fonte do catálogo, modelando o domínio como cinema.

**Descartado:** Ticketmaster Discovery. A API é mais rica em dados reais de local, mas o fluxo que ela sugere, de shows com pista e setores, se resolve por quantidade de ingressos e não por assento.

**Por quê:** o requisito de assento único é a garantia técnica mais interessante do desafio, e ela só aparece de verdade num mapa de assentos. Cinema também dá uma cadeia coerente: filme em cartaz → sessão → poltrona. O TMDb ainda fornece pôster e backdrop, o que resolve boa parte da carga visual sem produção de imagem.

---

## D2 · Identidade visual: recibo térmico sobre papel

**Decidido:** paleta de papel creme, tipografia monoespaçada (IBM Plex Mono), alinhamentos de cupom fiscal, tracejado como divisor. Seis cores no total.

**Descartado:** duas direções alternativas: uma escura com âmbar de marquise, outra editorial em branco com grid suíço.

**Por quê:** papel, monoespaçado e picote remetem ao bilhete de cinema antigo, o canhoto que se destacava na entrada. É o ar de cinema que o produto precisava ter, e nenhuma das outras duas direções entregava: escuro com âmbar puxa para aplicativo de streaming, e o editorial em branco puxa para revista.

O objeto que o sistema produz é um bilhete, então a interface adota a linguagem do próprio objeto. Essa coerência entre meio e produto é o que sustenta a decisão além do gosto pessoal.

**Regra que decorre daí:** o carmim `#A32B1C` é reservado a ação e atenção: assento selecionado, erro, recusa. Nunca decoração.

---

## D3 · Monoespaçado com uma exceção

**Decidido:** todo o sistema em IBM Plex Mono, exceto a sinopse vinda do TMDb, que usa IBM Plex Sans.

**Por quê:** monoespaçado alinha dado tabular sozinho, e o painel do organizador, os totais do checkout e os códigos de ingresso ganham com isso. Prosa corrida é o caso em que ele perde: a sinopse é o único texto longo do sistema, e forçá-la em mono cobraria legibilidade sem devolver nada. A fonte irmã preserva a coerência do conjunto.

---

## D4 · Estados de assento distinguíveis sem cor

**Decidido:** os cinco estados (livre, seu, ocupado, em espera, acessível) se diferenciam por forma e textura além de cor: contorno, preenchimento, hachura e círculo.

**Por quê:** o par crítico do mapa é carmim sobre bege, indistinguível para parte dos usuários com deficiência de visão de cores. Redundância de codificação resolve isso sem custo de implementação.

---

## D5 · Front sem framework de servidor

**Decidido:** React com Vite.

**Descartado:** Next.js.

**Por quê:** o back-end é o FastAPI. As funcionalidades que justificam o Next, renderização no servidor e rotas de API próprias, ou não têm uso aqui ou duplicariam responsabilidade que já vive na API. Vite entrega o mesmo resultado com menos superfície.

---

## D6 · Sala como entidade própria

**Decidido:** `Room` vira tabela, com `venue`, `name` e o layout (`rows`, `seats_per_row`). `Showing` passa a apontar para uma sala em vez de repetir esses dados; `venue` sai de `Event`.

**Descartado:** manter sala e layout como campos soltos em `Showing`, que era o modelo inicial.

**Por quê:** o layout é propriedade física da sala, não da exibição: "Sala 3" tem 8×12 lugares independentemente de qual filme passa nela. No modelo anterior, `rows` e `seats_per_row` viravam dado morto assim que os assentos eram gerados, e passariam a mentir sobre o conteúdo real de `seats` se alguém os editasse depois. Agora o layout é cadastrado uma vez e toda exibição naquela sala herda a mesma geometria.

`venue` migrou de `Event` para `Room` no mesmo movimento: normalizar a sala mantendo o local como texto solto no evento deixaria ambíguo a que cinema uma "Sala 3" pertence.

**Até onde a normalização vai:** revisto em D7.

---

## D7 · Cinema como entidade própria

**Decidido:** `Venue` vira tabela com `name`, `city`, `state` e `address`. `Room` aponta para ela em vez de guardar o nome do cinema como texto.

**Descartado:** manter o cinema como texto em `Room`, que era a posição adotada em D6.

**Por quê:** A busca que estrutura toda plataforma de ingresso é por **cidade e cinema**, não por título. Com o local como texto não existia campo de cidade, então filtrar por região era impossível, e listar cinemas dependeria de `SELECT DISTINCT venue`, frágil a qualquer divergência de digitação: "Cinemark Eldorado" e "cinemark eldorado" virariam dois cinemas.

A cidade é indexada porque é o primeiro filtro que o cliente aplica, antes mesmo de escolher filme.

---

## D8 · Cadastro revela e-mail já cadastrado, com limite de tentativas

**Decidido:** o cadastro responde `409` explicitamente quando o e-mail já tem conta. A exposição é compensada por limite de tentativas por IP e por conta.

**Descartado:** responder sempre sucesso e informar o resultado real por e-mail.

**Por quê:** a alternativa descartada é a solução correta: quem já tem conta recebe um aviso, quem não tem recebe o link de confirmação, e nada vaza para quem só está sondando. Mas ela depende de envio de e-mail, listado como fora de escopo no enunciado. Sem esse canal, esconder a informação apenas trocaria o vazamento por um usuário travado sem entender por que o cadastro não conclui.

**O que isso expõe:** enumeração de usuários. Quem tiver uma lista de e-mails descobre quais têm conta tentando cadastrar cada um. É a mesma informação que o login se recusa deliberadamente a entregar, já que ali senha errada e e-mail inexistente retornam resposta idêntica. Admitir a inconsistência é mais honesto do que fingir que o cuidado no login basta.

**Mitigação implementada:** duas janelas deslizantes independentes.

| Janela | Limite | Defende de |
|---|---|---|
| Cadastro por IP | 20 / hora | Varredura de lista de e-mails |
| Login por IP | 60 / 5 min | Volume anormal de rede |
| Login por conta | 8 / 15 min | Força bruta de senha |

Os limites por IP são folgados de propósito: escritório, universidade e operadora móvel colocam muita gente atrás de um endereço só, e apertar ali puniria usuário legítimo sem impedir quem distribui o ataque entre vários endereços. A defesa efetiva contra força bruta é a janela **por conta**, que independe de origem. Acerto de senha zera a contagem, para que erro de digitação não bloqueie o dono.

**Limitação conhecida:** a contagem vive em memória e zera quando o processo reinicia, o que ocorre no Render, que hiberna por inatividade. Persistir em banco custaria uma escrita por tentativa, o que transformaria o próprio limitador em vetor de esgotamento de disco. É mitigação de custo, não bloqueio absoluto, e fica declarada como tal no README.

---

## D9 · Sala travada depois da primeira venda

**Decidido:** a sala de uma exibição pode ser trocada enquanto não houver ingresso. Sem venda, o mapa é descartado e refeito no layout da sala nova. Com venda, a troca é recusada.

**Descartado:** travar a sala já na publicação, e permitir a troca com remapeamento dos ingressos vendidos.

**Por quê:** trocar de sala é operação real de cinema: projetor quebra, sessão vende mal e migra para uma sala menor, sessão esgota e é promovida para uma maior. Ignorar o caso deixaria o organizador sem saída legítima.

O que a troca quebra não é integridade referencial: `Seat` pertence à exibição, não à sala, então nenhum assento fica órfão. O que quebra é a correspondência com a sala física, porque a exibição passaria a anunciar "Sala 5" exibindo um mapa gerado a partir do layout da Sala 3, e o cliente compraria a F7 de uma sala que pode não ter fileira F.

Travar já na publicação seria mais simples, mas custaria o caso mais comum: publicar, notar a sala errada e corrigir antes de vender. O remapeamento dos ingressos é o que uma rede real faria, e exige interface de realocação e política de reembolso, que são sistema à parte.

**Onde a linha foi traçada:** o gatilho é a primeira venda, não a publicação. Preço, horário e áudio continuam editáveis mesmo com ingresso vendido: quem comprou pagou o valor registrado no pedido, e promoção é operação corriqueira.

---

## D10 · Sessão cancelada permanece visível, com motivo

**Decidido:** cancelar uma sessão não a remove. Ela ganha estado próprio e um campo de motivo em texto livre, exibido a quem tem ingresso: *"Sessão cancelada: problema no projetor."* Os ingressos passam a `cancelled` e os pedidos registram o reembolso simulado.

**Descartado:** remover a sessão do sistema, e cancelá-la silenciosamente sem justificativa.

**Por quê:** remover deixaria o ingresso do cliente desaparecer sem explicação: ele abriria "Meus ingressos" e encontraria um vazio, sem saber se perdeu o acesso, se foi golpe ou se o evento mudou. Cancelar sem motivo é pouco melhor: informa que algo aconteceu e esconde o quê.

O motivo em texto livre existe porque a causa é operacional e imprevisível: falha de equipamento, público mínimo não atingido, interdição da sala. Uma lista fechada de opções não cobriria os casos reais e obrigaria a escolher "outro" com frequência.

**Efeito colateral já resolvido:** liberar os assentos não exige código. O índice único é parcial em `status <> 'cancelled'`, então o ingresso cancelado sai do índice e a poltrona volta ao estoque sozinha. É a escolha de índice parcial, feita na modelagem inicial, pagando aqui.

**Pendente de implementação.** Depende do fluxo de compra existir para ter o que cancelar. Entra junto com ele.

**Beco sem saída que motivou a decisão:** a D9 recusa a troca de sala orientando "cancele a sessão e crie outra", mas remover sessão com ingresso também é recusado. Sem D10, o organizador com sala interditada e ingressos vendidos não tem saída nenhuma.

---

## D11 · Regra de negócio em módulos, não em classes de serviço

**Decidido:** vira classe o que guarda algo entre chamadas; vira função de módulo o que só transforma entrada em saída. A regra de negócio fica em arquivos próprios, como `seating.py`, `security.py` e `tmdb.py`, e não dentro das rotas.

**Descartado:** classes de serviço agrupando funções, e uma camada de acesso a dados por cima do SQLAlchemy.

**Por quê:** classe que não guarda nada não protege nada, porque em Python o próprio arquivo já agrupa funções, ao contrário de linguagens onde toda função precisa morar numa classe. E envolver o SQLAlchemy numa camada de acesso repetiria o que ele já entrega: a `Session` é exatamente essa camada, e a classe extra só encaminharia chamadas.

Onde há estado, a classe está lá: `TTLCache` e `SlidingWindow` guardam dados entre chamadas e as regras que os governam.

**Consequência:** o fluxo de reserva encadeia verificação de disponibilidade, trava com prazo, pagamento e emissão do ingresso. Isso não cabe dentro de uma rota, e vai para módulo próprio, por tamanho e não por paradigma.

---

## D12 · Sessão é recurso de primeiro nível

**Decidido:** operações sobre uma sessão específica ficam em `/showings/{id}`. Criar e listar sessões de um evento continuam em `/events/{id}/showings`.

**Descartado:** manter tudo aninhado sob `/events/`, como estava.

**Por quê:** as rotas de detalhe, edição, remoção e mapa de assentos não usam o `event_id`: ele aparecia na URL sem participar da resolução. Aninhamento que não identifica nada é ruído, e obrigaria o front a carregar o evento só para montar o endereço da sessão.

A convenção adotada é a usual: coleção sob o pai, item na raiz.

**Momento da mudança:** feita antes de o front existir. Depois do dia 4 custaria alterar os dois lados ao mesmo tempo.

---

## D13 · Recusa de pagamento não devolve a poltrona

**Decidido:** cartão recusado mantém as poltronas reservadas até o prazo de dez minutos vencer. O pedido fica em estado recusado, mas continua pagável.

**Descartado:** cancelar os ingressos e liberar as poltronas no instante da recusa, que era o comportamento anterior.

**Por quê:** a justificativa original, de que "segurar a poltrona puniria outros clientes por uma compra que não vai acontecer", não se sustenta. A reserva já tem prazo, então as poltronas nunca ficariam presas indefinidamente; e cartão negado quase sempre significa que a pessoa vai tentar outro, não que desistiu.

Do jeito anterior, a tela oferecia "tentar outro cartão" e o pedido já estava encerrado: qualquer nova tentativa falhava, e a escolha de poltronas se perdia por causa de um dígito errado. Nenhum checkout real se comporta assim.

**O prazo continua valendo:** recusa não estende a reserva. Pagar depois do vencimento é recusado, e os assentos voltam ao estoque pela liberação sob demanda.

---

## D14 · Uma reserva aberta por cliente e sessão

**Decidido:** criar uma reserva cancela a reserva aberta que o mesmo cliente já tivesse naquela sessão, devolvendo as poltronas anteriores ao estoque na hora.

**Descartado:** deixar as duas reservas coexistirem até a mais antiga vencer.

**Por quê:** o cliente que volta ao mapa para trocar de poltrona não está iniciando uma segunda compra: está corrigindo a primeira. Sem a substituição, as poltronas abandonadas ficariam retidas por dez minutos sem que ninguém as quisesse, e o cliente apareceria com dois pedidos abertos da mesma sessão, sem saber qual pagar.

**A regra é por sessão, não por cliente:** quem está comprando ingressos de dois filmes ao mesmo tempo mantém as duas reservas.

**Consequência na interface:** as poltronas da reserva aberta voltam ao mapa já selecionadas e editáveis, em vez de bloqueadas. Marcá-las como ocupadas faria o cliente pensar que perdeu a própria escolha.

---

## D15 · Ingresso cancelado sai da lista em dois prazos diferentes

**Decidido:** o ingresso cancelado deixa de aparecer em "Meus ingressos" depois de um prazo que depende de quem cancelou: trinta minutos quando foi o próprio cliente, até o horário da sessão quando foi o cinema. A linha nunca é apagada do banco.

**Descartado:** um prazo único para os dois casos, e sumir no instante do cancelamento.

**Por quê:** os dois cancelamentos têm leitores diferentes. Quem cancelou o próprio ingresso já sabe o motivo, e o único papel da janela é não fazer o bilhete evaporar no mesmo clique, já que desaparecimento instantâneo se lê como erro e não como confirmação. Quem teve a sessão cancelada pelo cinema precisa do oposto: a explicação tem de estar lá justamente perto da data em que iria, que é quando vai procurar. Um prazo só serviria mal aos dois.

**Filtro na consulta, nunca `DELETE`:** o ingresso é registro de uma compra que existiu, e o índice parcial de D1 depende do status da linha. Apagá-la trocaria uma lista limpa por um histórico falsificado.

**Custo:** a coluna `tickets.cancelled_at` passou a existir para que haja de onde contar o prazo, porque `status` sozinho não diz quando mudou. É o par de `used_at`, que existe pela mesma razão.

---

## D16 · Portaria: desfechos no corpo, e o lugar conferido antes do estado

**Decidido:** `POST /gate/validations` responde sempre 200 com um estado no corpo, nunca em código HTTP. O lugar a que o ingresso pertence é conferido antes do estado dele, e a marcação de uso é a própria escrita condicional.

**Revisto em D21:** eram cinco estados e a conferência era pelo evento. A lista subiu para seis e o vínculo passou a ser pela exibição. O que esta decisão fixa e continua valendo é a *forma* da resposta e a *ordem* das perguntas.

**Descartado:** traduzir os desfechos em códigos HTTP: 404 para inexistente, 409 para já utilizado. E resolver o estado com um `SELECT` antes do `UPDATE`.

**Por que o corpo e não o status:** os desfechos têm o mesmo posto. Quem lê é um operador com uma pessoa parada na frente, e um ingresso recusado é resposta, não falha de requisição. Espalhá-los por códigos faria a tela tratar metade dos casos no caminho de erro do cliente HTTP, onde não há corpo padronizado para carregar a poltrona, o nome ou o horário da entrada anterior.

**Por que o lugar antes do estado:** descobrir tarde que o ingresso é da sala ao lado já teria consumido um ingresso legítimo de outra portaria. Verificado: o ingresso recusado por `wrong_event` continua `valid` no banco.

**O estado de cancelado:** um ingresso reembolsado apresentado na porta é situação real, e chamá-lo de "inválido" faria o operador tratar como fraudador quem apenas cancelou e esqueceu. É a mesma razão que separa `wrong_event` de `invalid`, ou seja, a diferença entre "não deixe entrar" e "não deixe entrar aqui".

**Digitação manual:** o operador digita o `jti` quando a câmera falha, e aí não há assinatura para conferir. O que sustenta esse caminho é o `jti` ser um uuid4, com 122 bits que não se adivinham, somado ao papel de portaria exigido na rota. É um controle diferente do da garantia 2, não uma brecha nela: sem credencial de portaria o código digitado não vale nada.

---

## D17 · Deploy em três serviços, com o banco fora do Render

**Decidido:** API no Render, front na Vercel, banco no Neon. A infraestrutura da API fica em `render.yaml`, versionada.

**Descartado:** o Postgres gratuito do próprio Render, que reuniria banco e API num painel só. E função serverless para a API.

**Por que o banco fora:** o Postgres gratuito do Render expira em 30 dias. O sistema morreria sozinho depois da avaliação, e a primeira coisa que quem abrisse o link veria seria um erro de conexão. O Neon não expira.

**Por que não serverless:** o limitador de tentativas e o cache do TMDb vivem em memória. Numa função que sobe e morre a cada requisição, os dois perderiam o efeito, porque o limitador zeraria a contagem a cada tentativa, que é exatamente o que ele existe para impedir. Um processo de vida longa é requisito, não preferência.

**Migration no build e não no pre-deploy:** comando de pré-deploy exige instância paga. Com uma instância só e sem exigência de janela sem downtime, aplicar no build basta e mantém `alembic upgrade head` como o único caminho de mudança de schema.

**A escolha de região saiu errada, e o erro tem nome.** O Render está em `oregon` e o Neon em `sa-east-1`, São Paulo. Medido: uma ida ao banco custa 15ms do Brasil e cerca de 250ms do Oregon, porque atravessa o hemisfério. É o custo fixo que sobrou depois de a D37 cortar o número de idas, e explica os 0,75s de uma rota que faz uma consulta trivial.

O raciocínio que produziu o erro foi pôr o banco perto do usuário. **O banco tem de ficar perto da API, não perto do usuário:** o único cliente do Postgres é a API, e o usuário nunca fala com ele. Quem precisa estar perto do usuário é o front, e esse já está na borda da Vercel. A escolha otimizou uma conversa que não existe e penalizou a que existe, multiplicada por cada consulta de cada requisição.

**Não foi corrigido, e isso é decisão e não esquecimento.** Mover o banco significa criar outro projeto no Neon, migrar e trocar a credencial no Render, na véspera da entrega, para ganhar cerca de um segundo numa tela que já responde em um e meio. O risco de deixar o ambiente publicado fora do ar vale mais do que o segundo. Fica registrado como o primeiro item a mudar se o projeto continuar.

**O `pool_pre_ping` fica, apesar de custar uma ida inteira.** Ele dispara um `SELECT 1` antes de cada requisição para descartar conexão que o Neon derrubou por ociosidade. Trocá-lo por `pool_recycle` economizaria os 250ms, mas troca uma latência conhecida por uma falha ocasional de conexão, e num ambiente de demonstração o erro na tela custa mais caro que a espera.

---

## D18 · Credenciais de teste visíveis no ambiente publicado

**Decidido:** o painel de contas semeadas aparece também em produção, sob o rótulo "ambiente de demonstração", com a senha escrita ao lado.

**Descartado:** prendê-lo ao ambiente local, que era o comportamento anterior.

**Por quê:** as mesmas credenciais estão no README de um repositório público. Escondê-las na tela não removia a informação de lugar nenhum: era teatro de segurança, a aparência do cuidado sem o efeito. E cobrava caro justamente onde não se deve: os primeiros trinta segundos de quem abre o link são o momento mais valioso do projeto, e gastá-los procurando credenciais em outra aba é atrito no único caminho que importa.

**O que a decisão aceita:** vandalismo. Quem entrar como organizador pode cancelar sessões e deixar a demonstração quebrada. O risco já existia, porque o README entrega as credenciais de qualquer forma, e o estrago se desfaz com `python -m app.seed --reset`. O que muda é a facilidade, e ela é aceita porque o custo do dano é um minuto e o custo do atrito é a primeira impressão.

**O rótulo é parte da decisão:** dizer "ambiente de demonstração" na interface declara a natureza do que está no ar. Esconder as contas fingindo que aquilo é produção seria a postura menos honesta das duas.

---

## D19 · Catálogo mantém a tela anterior enquanto atualiza

**Decidido:** ao voltar ao catálogo, a última resposta daquela cidade continua na tela enquanto a nova requisição acontece. A busca ocorre sempre.

**Descartado:** cache com prazo de validade, e o comportamento anterior de apagar a tela antes de buscar.

**Por que não o cache:** a resposta do catálogo carrega `seats_available`, que é o que marca a sessão como esgotada. Guardá-la por alguns minutos faria o cliente clicar numa sessão que já lotou. Não seria catastrófico, já que o mapa é a fonte de verdade e a reserva perdida devolve a recusa clara de D1, mas trocaria um incômodo visual por informação errada, e informação errada é pior que espera.

**Por que não apagar a tela:** o `setFilmes(null)` anterior era o que fazia o catálogo piscar em branco a cada volta. Não era falta de cache; era a tela se apagando antes de ter o que colocar no lugar. Com a API hibernando no plano gratuito, isso vira meio minuto de tela vazia sobre conteúdo que já estava pronto.

**Consequência no erro:** uma atualização que falha com catálogo na tela não troca o conteúdo por um aviso. O aviso só aparece quando não há nada a mostrar, porque trocar dado útil por mensagem de erro puniria quem já tinha o que precisava.

---

## D20 · Leitura do QR por biblioteca, não pela API do navegador

**Decidido:** a portaria decodifica o QR com o `jsQR`, sobre quadros que ela mesma tira do vídeo.

**Descartado:** o `BarcodeDetector`, API nativa que faria o mesmo sem dependência alguma.

**Por quê:** nenhum navegador de iPhone implementa o `BarcodeDetector`: todos usam o WebKit, e a Apple mantém a API desligada. Numa portaria, o aparelho mais provável na mão de quem valida é um celular, e um caminho que falha em boa parte deles não é caminho. Detectar a API e cair para a biblioteca quando ela falta resolveria, mas ao custo de dois caminhos de código para o mesmo resultado, e o que não é exercitado no aparelho de quem desenvolve é o que quebra em produção.

**Custo aceito:** 50 KB comprimidos, mais que todo o resto do sistema junto. Pagos só por quem abre a portaria: a tela é carregada sob demanda, e quem está comprando ingresso nunca baixa o decodificador.

**A corrida que isto cria:** a câmera tenta decodificar seis vezes por segundo, e desligá-la depende de um novo render do React. Nesse intervalo o mesmo QR é lido de novo, e a segunda resposta voltaria `already_used`, trocando na tela o "válido" da primeira e mandando embora quem tinha ingresso bom. A trava é uma referência, não um estado, porque estado só vale no render seguinte e a corrida acontece antes dele. É a mesma classe de problema da garantia 3, um andar acima: lá o banco arbitra, aqui a tela precisa não se contradizer.

**Digitação manual não é plano B decorativo:** é o caminho quando a permissão é negada, quando não há câmera e quando a lente não coopera com a tela riscada de um celular. Fica sempre visível, nunca escondida atrás de "problemas?".

---

## D21 · Portaria vinculada à exibição, não ao filme

**Decidido:** `users.gate_showing_id` aponta para uma exibição. A validação separa dois recusados legítimos: `wrong_event` para outro filme, `wrong_showing` para outra sessão do mesmo filme. O QR passa a carregar `shw` em vez de `evt`, e o organizador cadastra e reaponta portarias pelo painel.

**Descartado:** manter o vínculo por evento e conferir uma janela de horário na validação. E manter o vínculo por evento apenas documentando o limite.

**O que estava errado:** com a portaria amarrada ao filme, nada impedia o ingresso da sessão das 22h de ser aceito na porta das 19h. Três consequências, nesta ordem de gravidade: a pessoa senta numa poltrona que pertence a outro comprador daquela sessão; entra num cinema onde não comprou nada, porque o mesmo filme passa em dois locais; e perde a sessão que pagou, já que o ingresso queima na entrada errada e volta como "já utilizado" no horário certo.

**Por que não a janela de horário:** ela fecharia o caso do horário e deixaria o do local aberto. A verificação contra o servidor mostrou o caso exato: o seed tem o mesmo filme começando à mesma hora em dois cinemas, e uma janela de tempo aceitaria o ingresso do cinema vizinho. Amarrar na exibição fecha horário, sala e cinema de uma vez, porque os três são propriedades dela.

**Por que dois recusados e não um:** a reação de quem opera é diferente. "Outro evento" manda a pessoa para outra sala; "outra sessão" manda para outro horário, às vezes outro dia. Um único estado obrigaria o operador a ler a ficha para descobrir o que dizer, e o ponto de o veredito ser lido de um metro é não precisar ler mais nada.

**O que isto destravou:** a tela da portaria passa a nomear a sessão que atende, com horário, cinema e sala, antes da primeira leitura. Com o vínculo por filme isso era impossível: o filme tem várias sessões, em locais diferentes, e não havia uma resposta única para "que porta é esta".

**O cadastro veio junto por necessidade:** uma portaria por exibição só se sustenta se trocar de sessão for barato, e desvincular é aceito de propósito, porque entre uma sessão e a seguinte a porta não deve aceitar nada.

**Revisto em D24:** a troca era feita pelo organizador, num `PATCH /gates/{id}` que já não existe. Passou a ser `PUT /gate/shift`, executado pelo próprio funcionário. O que esta decisão fixa e continua valendo é *o que* a portaria confere: a exibição, não o filme.

**Migração com conversão de dado:** a portaria que atendia um filme passou a atender a primeira exibição dele. Sem isso, quem já tinha portaria montada acordaria com ela desvinculada, e a única pista seria a recusa de todo ingresso.

---

## D22 · Primeiro cadastro vira organizador, e organizador promove organizador

**Decidido:** com a tabela `users` estritamente vazia, o primeiro cadastro nasce organizador. Dali em diante, um organizador promove uma conta existente pelo painel. O papel nunca vem do corpo da requisição.

**Descartado:** comando de linha no estilo `createsuperuser`, código de convite em variável de ambiente, e cadastro aberto como o da Sympla.

**Por que não o comando de linha:** é o padrão consagrado, e não funciona aqui. O plano gratuito do Render **não dá acesso ao shell do serviço**, então um comando resolveria só na máquina de quem desenvolve e deixaria a instalação publicada sem caminho nenhum para o primeiro organizador. Foi o argumento que derrubou a alternativa mais óbvia.

**Por que não o cadastro aberto:** é o modelo real desta categoria de produto: na Sympla qualquer pessoa cria evento, e o que se exige é CPF, para repassar dinheiro. Aqui ele está bloqueado por uma razão concreta: `venues` não tem dono. Qualquer organizador cadastra cinema e cria sala em cinema alheio, e esse cadastro alimenta o filtro público. Abrir o papel sem antes cercar o local entregaria o catálogo a quem aparecesse. O caminho existe, que é dar `organizer_id` ao `Venue`, e não foi percorrido por escopo.

**Por que promoção e não criação:** criar a conta pelo painel obrigaria o organizador a inventar uma senha e entregá-la por algum canal, e senha que trafega por mensagem fica no histórico de alguém. Aqui a conta já existe, e o que se concede é só o papel.

**Escolha em lista, não digitação:** promover exige apontar quem, e digitar o e-mail exige saber de cor o endereço com que a pessoa se cadastrou. Erra calado: um caractere trocado devolve "conta não encontrada" sem dizer qual era a certa. A lista oferecida é a dos funcionários do organizador, que é quem se espera promover.

**Promover encerra o vínculo de funcionário:** os papéis são exclusivos. Acumular os dois daria a quem opera a porta o poder de publicar e cancelar sessões, e é justamente essa separação que faz o papel de portaria valer alguma coisa. Quem precisar dos dois usa duas contas, e aí fica registrado que são duas pessoas na mesma sessão.

**A janela que isto abre, declarada:** o deploy aplica as migrations mas não roda o seed. Uma instalação nova sobe com `users` vazia e URL pública, e nesse intervalo quem se cadastrar primeiro vira organizador. É a mesma janela de qualquer instalador de primeira execução, e a mitigação é operacional: criar a conta imediatamente depois do primeiro deploy. A condição é a tabela **vazia**, e não "não existe organizador", para que a regra se feche no primeiro cadastro e nunca reabra, nem se um organizador for removido depois.

---

## D23 · Cidade e UF escolhidas em lista, com o código do IBGE guardado

**Decidido:** a UF vem de uma constante de 27 valores no servidor; o município, da API de localidades do IBGE. O cadastro envia a UF e o **código** do município, e o nome é resolvido no servidor. `venues.city_ibge_id` guarda o código, e é por ele que o catálogo agrupa e filtra.

**Descartado:** manter cidade e UF como texto livre, normalizando na entrada.

**Por quê:** o filtro do catálogo agrupa cinemas por cidade. Com texto livre, "São Paulo" e "sao paulo" viravam **duas cidades** na lista de filtros, e nenhuma validação de formato pega isso, porque as duas são strings perfeitamente válidas. Normalizar acento e caixa reduziria o problema sem resolvê-lo: sobrariam "Sao Paulo", "S. Paulo" e os erros de digitação que ninguém antecipa.

**Por que o código e não só o nome:** **nome de cidade não é único no Brasil.** Há dezenas de "Bom Jesus", "Santa Luzia" e "Bonito" em estados diferentes. Agrupar por texto juntaria cidades que não têm relação nenhuma, e o cliente veria sessões de outro estado sob o nome da cidade dele. O código do IBGE é a única chave que distingue.

**O nome nunca vem do cliente:** ele é resolvido contra a lista do IBGE na gravação. Aceitá-lo do corpo da requisição reabriria exatamente a porta que esta decisão fecha.

**A UF não vem da rede:** são 27 e não mudam desde 1988. Buscá-las seria trocar uma constante por um ponto de falha, e a lista é o primeiro campo do formulário, de modo que falhar ali travaria o cadastro inteiro.

**Dependência externa assumida, com saída:** o IBGE fora do ar impede cadastrar cinema novo, e nada mais que isso: o catálogo, a compra e a portaria não passam por lá. A resposta nesse caso é um 503 que diz o que aconteceu, e não um erro mudo. O seed traz os códigos escritos, para semear sem internet.

---

## D24 · Portaria é posto, funcionário é a conta, e o turno é dele

**Decidido:** a conta é de um **funcionário**, não de uma portaria. Portaria é a tela que ele abre para trabalhar. Dois campos com donos diferentes: `gate_venue_id` é o cinema onde a pessoa trabalha, definido pelo organizador na criação; `gate_showing_id` é a sessão do turno, escolhida pelo **próprio funcionário** em `PUT /gate/shift`, entre as sessões daquele cinema.

**O vocabulário importa:** enquanto a conta se chamava "portaria", parecia natural criar uma por sessão, porque postos são efêmeros. Chamando de funcionário, a mesma pergunta soa absurda: ninguém contrata alguém por duas horas e demite quando o filme acaba.

**Descartado:** conta criada por sessão, código de pareamento por dispositivo, e portaria como modo da conta do organizador.

**O que estava errado:** a conta era criada apontando para uma exibição. Terminada a sessão, sobrava um e-mail e uma senha sem serventia. Operar uma noite exigiria criar e distribuir credenciais a cada duas horas, e senha que se multiplica é senha que se anota num papel colado no balcão.

**Por que não o código de pareamento:** foi a alternativa que eu propus primeiro, e ela tem um furo. O código é segredo ao portador: quem o ouvir, vir na tela ou receber encaminhado vira portaria. O estrago não é validar o próprio ingresso, que só o queima: é **validar o dos outros**, fazendo o titular legítimo levar "já utilizado" na cara. Um código curto, feito para ser ditado por telefone, é exatamente o tipo de segredo que vaza.

**Por que não o modo do organizador:** quem fica na porta seguraria um aparelho logado com a conta que publica e cancela sessões. Menor privilégio deixa de existir.

**Por que o funcionário escolhe:** o organizador não está na porta às onze da noite. Reapontar cada portaria a cada duas horas não sobrevive a uma noite de operação real, e a alternativa seria o operador ligar para alguém a cada troca. A liberdade é escolher **entre as sessões do próprio cinema**, e essa lista é montada no servidor: mandar um id de fora recebe 404.

**Escopo por cinema e não por organizador** porque é assim que emprego funciona: a pessoa trabalha num lugar, não para um catálogo inteiro. É o que impede alguém do Belas Artes de validar ingresso do Odeon.

**Ganho colateral:** `validated_by` passa a apontar para uma pessoa, não para um posto anônimo. Se um ingresso foi validado errado, há a quem perguntar.

**A janela de sessões oferecidas** vai de quatro horas atrás a três dias adiante. O passado recente porque a sessão que começou há pouco ainda tem gente entrando; o futuro curto porque uma lista com o mês inteiro esconderia a de hoje. Sessão cancelada não aparece: ela não recebe ninguém.

---

## D25 · Cadastro editável, remoção só do que está vazio

**Decidido:** cinema, sala e funcionário ganham edição e remoção. A remoção é recusada quando levaria algo junto: cinema com sala, sala com sessão, funcionário que já validou ingresso.

**Descartado:** remoção em cascata, e cadastro imutável que se corrige recriando.

**Por que não recriar:** o cinema tem salas, e as salas têm sessões vendidas. Um erro de digitação no endereço obrigaria a desmontar a estrutura inteira, e no caminho os ingressos comprados sumiriam.

**Por que não a cascata:** apagar um cinema levaria salas, sessões e ingressos, e quem comprou perderia o ingresso por causa de uma limpeza de cadastro. Exigir esvaziar antes torna a consequência visível passo a passo, em vez de escondê-la atrás de uma confirmação genérica.

**Funcionário que validou não sai:** `tickets.validated_by` aponta para quem estava na porta. Apagar a conta exigiria zerar esse campo, e o histórico deixaria de dizer quem deixou cada pessoa entrar, que é metade do motivo de a conta ser de gente e não de posto (D24). A saída oferecida é tirar o cinema: a conta para de validar e o histórico continua de pé.

**Layout de sala continua editável com sessões marcadas.** Os assentos pertencem à exibição e são gerados na publicação (D6), então a mudança vale para as próximas e não reescreve mapa já vendido. Travar aqui obrigaria a criar uma sala nova para corrigir um número errado.

**Cidade só muda em par com a UF:** mandar uma sem a outra deixaria o código do município apontando para outro estado, que é o erro que a D23 existe para fechar.

**Escopo da equipe segue o do cadastro de locais.** A primeira versão recortava por "cinemas onde tenho sessão", e quebrava no caso mais comum, que é cinema recém-criado, funcionário cadastrado e nenhuma sessão ainda, deixando o cadastro impossível de corrigir. Como `Venue` não tem dono (D22), qualquer organizador já cadastra cinema e cria sala em cinema alheio: recortar só a equipe seria cerca isolada em volta de terreno aberto. Fechar isso de verdade é dar dono ao `Venue`, e está declarado nas limitações.

---

## D26 · Cobertura por sessão, não por funcionário

**Decidido:** o painel mostra, acima da tabela de equipe, as sessões que começam nas próximas doze horas e quem está na porta de cada uma. Sessão sem ninguém aparece em carmim, com barra à esquerda.

**Descartado:** deixar só a coluna "atendendo agora" na tabela de funcionários.

**Por quê:** a tabela responde "o que o João está atendendo?". Quem opera um cinema pergunta o contrário: "a sessão das 21:30 tem alguém na porta?". A resposta saía de cruzar duas colunas na cabeça, o que funciona com três funcionários e falha numa noite cheia. E o erro dessa conta só aparece quando a fila já se formou.

**Consequência de o turno ser escolhido pelo funcionário (D24):** ao tirar o organizador da virada de cada sessão, tirou-se também a visão dele sobre quem está onde. Este bloco devolve a visão sem devolver o controle: é leitura, não comando. Dois lugares comandando o mesmo campo fariam a tela de quem opera mentir sobre o que ele está atendendo.

**A janela é a mesma da escolha de turno**, e não uma própria. A primeira versão usava doze horas, e a verificação mostrou o defeito: um gerente olhando de manhã não via a sessão da noite, e nem o cenário semeado aparecia. Pior que o prazo curto era serem dois prazos, porque o organizador veria uma sessão descoberta que ninguém consegue assumir, ou deixaria de ver uma que já pode ser coberta. Uma janela só mantém as duas telas falando da mesma realidade.

**Recortado por evento e não por cinema:** eventos têm dono no modelo, cinemas não (D22). É o único recorte que se sustenta hoje.

**A coluna da tabela continua**, porque as duas perguntas são legítimas: a lista serve para agir antes da sessão, a coluna para conferir quem está fora de turno.

---

## D27 · Organizador abre a portaria, e o papel se revoga sem apagar a conta

**Decidido:** o organizador valida ingressos pelo próprio papel, sem conta separada. O escopo dele não é um cinema, e sim os eventos que publicou. Um organizador pode corrigir o nome de outro e revogar o papel de outro. O primeiro organizador é intocável para revogação, mas editável.

**Descartado:** exigir uma segunda conta de funcionário para o organizador validar. E apagar a conta ao revogar o papel.

**Por que acumular aqui:** num cinema pequeno quem publica a sessão é quem fica na porta. Obrigá-lo a manter duas contas seria burocracia sem ganho de segurança, porque ele já pode tudo o que a portaria pode, e mais. A separação de papéis existe para **limitar** o funcionário, não para limitar quem já tem todo o poder.

**Escopo por evento e não por cinema:** o organizador não tem um cinema onde trabalha, tem os eventos que publicou. Amarrá-lo a um `gate_venue_id` seria inventar um vínculo empregatício que não existe.

**Revogar não apaga:** o que a conta publicou continua de pé. Apagar levaria junto eventos, sessões e ingressos vendidos, e quem comprou perderia o ingresso porque alguém saiu da equipe. Para qual papel ela volta é a D32.

**O primeiro organizador é âncora:** ele nasce do primeiro cadastro em banco vazio (D22), e o cadastro público não cria outro depois que a tabela deixou de estar vazia. Removê-lo abriria a porta para a instalação ficar sem ninguém que publique. Editar o nome dele não tem esse risco, então continua liberado.

**Ninguém revoga a si mesmo:** não por princípio, e sim porque o clique seria irreversível pela própria tela, já que a pessoa perderia o acesso que usaria para desfazer.

**Vários funcionários na mesma sessão são permitidos**, e isso está certo. As plataformas de ingresso tratam múltiplos aparelhos no mesmo portão como o caso normal, e o que exigem é detecção de duplicata entre eles, que aqui já é a garantia 3, resolvida no banco pela escrita condicional. Limitar a um por sessão quebraria a entrada de qualquer sessão cheia, que é justamente quando mais gente é necessária na porta.

---

## D28 · Cidade digitada à mão quando o IBGE não responde

**Decidido:** o campo de cidade vira texto livre **apenas** quando a lista de municípios falha. O nome oficial sempre vence: com o IBGE no ar, o texto enviado é ignorado.

**Descartado:** deixar o cadastro de cinema indisponível enquanto o IBGE estiver fora.

**Por quê:** a D23 fechou o texto livre para acabar com "São Paulo" e "sao paulo" convivendo. Mas ela criou uma dependência dura: sem o IBGE, não se cadastra cinema nenhum. Um serviço de terceiro fora do ar não pode travar o cadastro do sistema inteiro.

**A regra que mantém a D23 de pé:** o servidor só olha o campo manual depois de a consulta ao IBGE ter falhado com 503. Não é o cliente que decide usar o atalho: se a lista responde, o nome vem dela. Assim a saída de emergência não vira porta dos fundos para reintroduzir o texto livre.

**O que se aceita perder:** nesse caso o `city_ibge_id` gravado pode não corresponder ao nome digitado, e o agrupamento do catálogo fica pelo código. É preferível a um cadastro impossível, e a divergência se corrige editando o cinema quando o IBGE voltar.

---

## D29 · Catálogo único, sem dono por organizador

**Decidido:** qualquer organizador vê e opera qualquer evento, sessão, cinema e sala. `events.organizer_id` continua no modelo como registro de quem publicou, e deixou de ser cerca de acesso. `GET /events/mine` virou `GET /events/managed`.

**Descartado:** manter cada organizador com o próprio catálogo, que era o comportamento anterior.

**Por quê:** o sistema é de um cinema, não um marketplace de produtores independentes. Uma equipe que administra a mesma operação precisa enxergar a mesma realidade, porque com recorte por dono quem cobrisse o turno do colega não conseguiria cancelar a sessão dele com o projetor quebrado.

**A inconsistência que isto resolve:** `Venue` nunca teve dono, então qualquer organizador já cadastrava cinema e criava sala em cinema alheio, enquanto eventos eram privados. Metade do cadastro era compartilhada e a outra metade não, sem que nada justificasse a linha entre elas.

**O que não mudou:** cliente e funcionário continuam sem acesso ao painel. Unificar é entre organizadores, não com o resto do mundo. E `404` para evento inexistente continua: sumiu a cerca de dono, não a checagem de existência.

**O que se perde:** o sistema deixa de suportar dois cinemas independentes na mesma instalação. É uma troca deliberada, porque o produto é um cinema com uma equipe, e fingir multilocação sem construí-la de verdade seria pior que assumir a escolha.

---

## D30 · Um filme, um evento, e rascunho é o único apagável

**Decidido:** criar evento com um `tmdb_id` que já está no catálogo é recusado, com o nome do evento existente na mensagem. Apagar só vale para rascunho sem sessões.

**Descartado:** permitir o mesmo filme duas vezes, e apagar em cascata.

**Por que a unicidade:** dois eventos do mesmo filme produziriam dois blocos idênticos no catálogo, com as sessões repartidas entre eles. O cliente veria "Duna" duas vezes e teria de abrir os dois para achar o horário que procura. Um filme é um evento; as sessões se penduram nele.

**A mensagem nomeia o evento existente** porque o erro sozinho não resolve o problema de quem o recebe: a pessoa queria criar uma sessão, e precisa saber onde criá-la.

**Por que só rascunho:** publicado pode ter ingresso vendido, e apagar levaria junto o comprovante de quem comprou. Despublicar existe para tirar do ar sem destruir histórico, e para o evento que já vendeu é o mais longe que dá.

**Por que sem sessões:** exigir esvaziar antes torna a consequência visível passo a passo, em vez de escondê-la atrás de uma confirmação genérica. É a mesma regra de cinema e sala (D25).

**O botão só aparece quando a remoção é possível.** Oferecer e responder 409 seria prometer o que não se pode cumprir.

**Efeito colateral no teste:** o duplo do TMDb devolvia sempre o mesmo filme, independentemente do que fosse pedido. Isso o fazia mentir, porque dois filmes diferentes voltavam como o mesmo, e nenhum teste conseguiria exercitar esta regra. Passou a devolver o id pedido.

---

## D31 · Zoom no mapa por roda, pinça e barra

**Decidido:** o mapa amplia pela roda do mouse, por pinça no toque, e por uma barra deslizante ao lado. Arrastar move o mapa no toque. A rolagem vale nos dois eixos.

**Descartado:** só rolagem, e um botão binário de "ver a sala inteira".

**O defeito que motivou tudo:** ao criar o invólucro de rolagem para consertar o corte lateral, ele nasceu com `overflow-y: hidden`. Numa sala alta isso cortava as fileiras de cima e as deixava **inalcançáveis**: nem rolando se chegava nelas. Uma sala de oito fileiras não mostrava o problema; uma de vinte escondia metade.

**O alerta que se aceita:** a documentação de gráficos interativos registra que roda do mouse para zoom atrapalha rolar a página, e que a prática comum é exigir Ctrl. A troca é aceita aqui por duas razões: no computador a tela da compra não rola, já que quem rola é a área do mapa, e arrastar assume o papel de mover, então nada fica inalcançável. Exigir Ctrl seria esconder o zoom atrás de um atalho que ninguém descobre no meio de uma compra.

**Três entradas para a mesma coisa** porque são três contextos: roda no computador, pinça no celular, e a barra para quem não tem roda ou não descobre o gesto. Gesto que não aparece na tela é gesto que não se descobre.

**Ampliação em torno do centro visível:** ampliar a partir do canto jogaria a vista para longe da poltrona que a pessoa estava olhando, e a queixa que a literatura registra sobre plantas grandes é justamente perder-se ao navegar.

**`touch-action: none` é obrigatório**, não preferência: sem isso o navegador rola por conta própria e os dois gestos disputam o mesmo toque, fazendo a pinça funcionar só de vez em quando.

**Arrastar move só no toque.** No mouse, arrastar sobre uma poltrona seria confundido com a intenção de escolhê-la.

---

## D32 · Promoção e revogação se desfazem uma à outra

**Decidido:** revogar o papel de organizador devolve a conta a **funcionário**, não a cliente, e sem cinema. O organizador alcança a tela da portaria pelo próprio papel, pelo mesmo elo de navegação que o funcionário usa.

**Descartado:** revogar para cliente, como era. E restaurar automaticamente o cinema que a pessoa tinha antes da promoção.

**O defeito:** promover era caminho de mão única. `promote_organizer` zera o vínculo com o cinema e troca o papel; `demote_organizer` devolvia `Role.CUSTOMER`. Quem subisse e descesse virava cliente, e o e-mail ficava **queimado**, porque `create_gate` recusa e-mail já existente e não há recuperação de senha no escopo. A conta que a D27 fazia questão de preservar sobrevivia sem servir para nada. O ciclo apareceu no banco semeado: a conta de portaria estava como cliente, e a equipe, vazia.

**Simetria é a regra:** uma operação e a sua inversa precisam se cancelar. Promover tira o funcionário da equipe; revogar devolve. Sem isso, "revogar" é um apagamento disfarçado, pior que apagar, porque deixa o registro ocupando o e-mail.

**O cinema não volta:** a promoção o desfez, e o cargo na volta pode ser outro. A conta reaparece na aba *Equipe* sem cinema, que é exatamente o estado que pede a atenção de quem coordena, e a listagem já inclui os sem cinema de propósito (D25). Guardar o vínculo anterior exigiria uma coluna para lembrar um dado que perde validade no instante em que é gravado.

**O turno morre com o papel:** a sessão que a pessoa atendia como organizador não é herdada pelo funcionário que ela volta a ser. Turno é escolha de quem trabalha, a cada virada (D24).

**O organizador na portaria já valia na API** desde a D27: `_sessoes_disponiveis` abre o escopo inteiro para ele, e a validação nunca exigiu `Role.GATE`. Só o front escondia: a navegação mostrava o elo apenas para `role === 'gate'`, e a tela recusava com "entre com uma conta de funcionário". Uma permissão que existe e não tem caminho na interface é uma permissão que não existe.

---

## D33 · Cobertura conta quem está na porta, não quem tem o cargo

**Decidido:** a lista de cobertura inclui qualquer conta com turno escolhido, funcionário ou organizador, e marca o organizador como tal. A tabela de funcionários continua só com funcionários.

**Descartado:** contar apenas `Role.GATE`, como era. E colocar o organizador dentro da tabela de funcionários.

**O defeito:** a consulta filtrava `User.role == Role.GATE`. Como o organizador assume turno pelo próprio papel (D27), a sessão que ele estava atendendo aparecia em carmim, como **descoberta**. A D26 existe para responder "esta sessão tem alguém na porta?", e respondia errado justamente quando quem cobria era quem lê a tela.

**Por que não entra na tabela de funcionários:** aquela tabela é superfície de edição, com nome, cinema e remoção. Organizador não tem cinema onde trabalha (D27), não é removível por lá, e a senha dele não é do cadastro de equipe. Listá-lo ofereceria ações que falhariam. As duas listas respondem perguntas diferentes: uma é a escala, a outra é o estado da noite.

**A marca é etiqueta, não cor:** o carmim já significa "sem ninguém", e reusá-lo no organizador diria "atenção" sobre uma porta que está coberta.

**O rótulo mudou junto:** era "N sem funcionário alocado", e virou "N sem ninguém na porta". A contagem sempre foi de portas descobertas, não de vagas na escala, e o texto é que descrevia o filtro antigo em vez do que a lista mede.

---

## D34 · Compose sobe o sistema sem credencial da máquina

**Decidido:** `docker compose up --build` levanta banco, API e front. O Postgres é um contêiner, a chave de assinatura é um valor de desenvolvimento no próprio arquivo, e a do TMDb é opcional. Migration e seed rodam no arranque da API.

**Descartado:** apontar o Compose para a Neon, reaproveitando o `.env` da máquina. E deixar migration e seed como dois comandos manuais depois de subir.

**Por que banco em contêiner:** o pedágio que o Compose existe para remover é justamente o cadastro na Neon. Reaproveitar o `.env` traria dois defeitos de uma vez: quem clona o repositório não tem esse arquivo, e quem tem apontaria os contêineres para o banco de **produção**, onde um `--reset` apaga o cenário publicado.

**As chaves não vazam para a imagem:** o `.env` está nos dois `.dockerignore`. As variáveis de ambiente têm precedência sobre o arquivo no `pydantic-settings`, então copiá-lo não mudaria o comportamento, mas gravaria a string da Neon e a chave dos ingressos numa camada da imagem, e imagem se compartilha.

**Chave de assinatura diferente da de produção, de propósito:** é ela que assina os ingressos. Sendo outra, um QR emitido no Compose não vale no ambiente publicado e vice-versa. Os dois ficam isolados por construção, e não por disciplina.

**A URL da API é argumento de build, não variável de execução:** o Vite embute as `VITE_*` no bundle durante o build, e declará-la em `environment` não teria efeito nenhum. E é `localhost` e não `api`, porque quem faz a chamada é o navegador de fora, onde o nome do serviço não resolve.

**Base Debian na API, não Alpine:** `psycopg[binary]` publica wheel para glibc. Em musl o pip cairia para compilar o driver, exigindo toolchain e cabeçalhos do libpq.

**O volume monta `/var/lib/postgresql`, não `.../data`:** do Postgres 18 em diante a imagem guarda os dados numa subpasta por versão maior, para que a atualização use `pg_upgrade --link` sem cruzar a fronteira do ponto de montagem. Montado no caminho antigo, que é o de toda a documentação escrita até 2025, o contêiner recusa subir em vez de arriscar corromper dados de uma versão anterior.

**Espera por `healthcheck`, não por `sleep`:** o Postgres só aceita conexão depois de inicializar o cluster, e tempo fixo ora sobra ora falta, de modo que a migration falharia de forma intermitente, que é o pior modo de falhar.

**O seed roda em toda subida** porque é idempotente: já semeado, não faz nada. Condicioná-lo exigiria guardar estado fora do banco para responder uma pergunta que o próprio banco responde.

---

## D35 · Encolher a sala é recusado sobre poltrona vendida

**Decidido:** o layout da sala continua editável com sessões marcadas, menos quando a redução deixaria uma poltrona já vendida fora do mapa. A recusa nomeia a poltrona.

**Descartado:** travar a edição do layout depois da primeira venda, e deixar como estava, permitindo qualquer redução.

**O defeito:** a D9 impede trocar a **sala de uma exibição** depois da primeira venda, justamente para que ninguém fique com ingresso da F7 numa sala sem fileira F. Mas nada impedia mexer nas **dimensões da própria sala**. Reproduzido contra a API: sala 8x12, poltrona H12 vendida, `PATCH` para 3x4 devolvia 200, e o cliente ficava com um ingresso válido para uma fileira que o cadastro passou a negar.

**Por que não travar tudo:** o caso comum é corrigir um número errado no cadastro, e travar obrigaria a criar uma sala nova para consertar um dígito. O perigoso é um subconjunto pequeno, e é ele que a checagem isola.

**Cancelado não conta:** a poltrona cancelada voltou ao estoque, então não há lugar a preservar. É a mesma cláusula do índice único parcial da garantia 1, aplicada de novo.

**A consulta pega o extremo, não a lista:** basta a maior fileira e a maior poltrona já vendidas, porque o mapa é retangular. Percorrer ingresso por ingresso responderia a mesma pergunta pagando mais caro.

---

## D36 · Apagar sessão exige cancelar antes, e o que passou pela portaria não sai

**Decidido:** a sessão sai do sistema quando não resta ingresso ativo nela. Sessão que vendeu passa antes pelo cancelamento, que é o passo que informa o motivo a quem comprou e devolve o valor. Sessão com ingresso já validado na portaria não sai nunca. Apagar leva junto poltronas, ingressos cancelados e pedidos.

**Descartado:** um botão único que apaga a sessão com tudo embaixo dela, e o oposto, esconder sessões passadas atrás de um filtro sem nunca remover nada.

**Por que não o botão único:** seria a mesma confirmação removendo um horário digitado errado, que não afeta ninguém, e o ingresso que alguém pagou. A tela não teria como mostrar que são coisas diferentes, e a diferença é a única coisa que importa ali. Separar em dois passos custa um clique e torna a consequência visível antes de acontecer.

**Por que não o filtro:** esconder resolve a tabela do painel e não resolve o pedido, que é tirar do sistema a sessão que não vai acontecer. Sessão escondida continua no catálogo público enquanto for futura.

**Por que o utilizado trava para sempre:** a garantia 3 existe para que ninguém entre duas vezes com o mesmo ingresso, e o que a sustenta é a linha que registra a entrada. Apagar a sessão apagaria esse registro, e a garantia passaria a valer só até alguém decidir limpar o painel. Cancelar já respeita isso: o `cancel_showing` não reverte ingresso utilizado, porque a pessoa entrou.

**A limpeza é explícita porque o banco não a faz:** `tickets.seat_id` e `orders.showing_id` não têm cascata. As poltronas saem junto com a sessão pela cascata do ORM, e sem apagar ingresso e pedido antes sobrariam linhas apontando para o vazio. A ordem é a inversa das dependências: `share_links`, `tickets`, `orders`, sessão.

**O botão de apagar evento passou a aparecer sempre**, inclusive quando não dá. Escondê-lo enquanto o evento estava publicado ou tinha sessão fazia a remoção parecer inexistente, e quem queria tirar um filme do ar não tinha como descobrir que o caminho é despublicar, esvaziar e então apagar. Clicável de propósito, com `aria-disabled` em vez de `disabled`: é o clique que responde qual dos dois passos ainda falta, e `disabled` tira do foco justamente o elemento que tem a explicação.

---

## D37 · Ocupação em lote, e o orçamento de idas ao banco virou teste

**Decidido:** toda rota que devolve uma coleção resolve totais e ocupação em consultas agrupadas, nunca uma chamada por linha. Dois testes contam as idas ao banco e falham se o custo voltar a crescer com o número de linhas.

**Descartado:** cache na aplicação, e paginar a lista de sessões do painel.

**O defeito:** `GET /events/{id}/showings` chamava `uma_sessao` por linha, e cada chamada custava três consultas. Um evento com 13 sessões fazia 39 idas ao banco. O catálogo público já resolvia todos os eventos em três, porque busca totais e ocupações com um `IN` e um `GROUP BY`; a rota do painel nunca tinha recebido o mesmo tratamento.

**Por que não apareceu antes:** o custo do N+1 é o número de idas, não o trabalho de cada uma. Em desenvolvimento a API e o Postgres estão na mesma máquina e a ida é quase de graça, então 39 somavam 0,62s e passavam despercebidas. Com a API no Render e o banco no Neon, em serviços separados, as mesmas 39 viraram 9 segundos. O defeito é invisível de um lado e dominante do outro, e é por isso que ele precisa falhar num teste em vez de esperar alguém reclamar.

**Por que não cache:** invalidar é o problema, não guardar. A ocupação muda a cada compra, e um cache aqui trocaria uma lentidão honesta por um número errado na tela do organizador, que é justamente quem precisa do número certo.

**Por que não paginar:** paginar reduziria o número de linhas por resposta sem reduzir o custo por linha, e a lista do painel tem dezenas de sessões, não milhares. Corrige o sintoma na metade dos casos e deixa o padrão de pé.

**O orçamento é comparativo, não absoluto:** o teste não fixa "três consultas", fixa que o custo de 12 sessões é igual ao de 1. Um número absoluto quebraria a cada mudança inocente de consulta e seria atualizado sem ninguém pensar; a comparação só quebra quando o padrão volta.
