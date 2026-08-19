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

**Cartão recusado deixava a compra num beco sem saída.**
Percorrendo o fluxo, digitei um cartão inválido e o sistema ofereceu "tentar outro cartão" — mas qualquer nova tentativa falhava. O agente havia decidido que recusa devolve as poltronas na hora, com o argumento de que segurá-las puniria outros clientes. O argumento não se sustenta: a reserva já tem prazo, e cartão negado quase sempre significa que a pessoa vai tentar outro. Um dígito errado custava a escolha inteira de poltronas. Virou a decisão D13, e três testes substituíram o que afirmava o contrário.

**Poltronas próprias apareciam como de terceiros.**
Reservei poltronas, fui ao pagamento e voltei ao mapa: as minhas estavam marcadas como ocupadas, indistinguíveis das de outra pessoa, e não havia caminho de volta ao pedido. A primeira correção do agente as marcou com um estado próprio, mas bloqueadas. Recusei: se a poltrona é minha, devo poder desmarcar, trocar, escolher outra. A versão final devolve a reserva já selecionada e editável, e reservar de novo substitui a anterior liberando as poltronas antigas na hora. Virou a decisão D14.

**Retorno explícito em todas as telas.**
Cobrei que não dava para voltar do mapa ao catálogo, nem do pagamento ao mapa. O botão do navegador existe, mas não é visível dentro da página — e num fluxo de compra a pessoa precisa ver que dá para recuar sem perder o que escolheu.

**Confirmação de cancelamento com a cara do navegador.**
O agente usou `window.confirm` e `window.prompt` para confirmar cancelamentos. Apontei que aquilo destoava de tudo: caixa cinza do sistema operacional, tipografia alheia, e um campo de texto sem rótulo pedindo o motivo que quem comprou ingresso iria ler. Virou um diálogo próprio, desenhado como a via do estabelecimento — papel, picote separando cabeçalho e ações, carmim só no botão que destrói. Construído sobre o elemento `<dialog>` nativo, que já traz prisão de foco, fechamento pelo Esc e retorno do foco ao botão de origem.

**Ingresso cancelado ficava na lista para sempre.**
Perguntei se fazia sentido o bilhete cancelado nunca sair de "Meus ingressos". Não fazia — mas a resposta óbvia, um prazo único, também não: quem cancela o próprio ingresso já sabe o motivo, enquanto quem teve a sessão cancelada precisa lê-lo perto da data em que iria. Ficaram dois prazos, e o filtro na consulta em vez de apagar a linha. Virou a decisão D15.

**Contas de teste escondidas em produção sem motivo real.**
O agente prendeu o painel de contas semeadas ao ambiente local, argumentando que expô-las em produção convidaria a testar credenciais. Perguntei se esconder era mesmo a melhor ideia. Não era: as mesmas credenciais estão publicadas no README de um repositório público, então a omissão na tela não protegia nada e cobrava de quem avalia uma ida ao GitHub. Passou a aparecer, rotulado como ambiente de demonstração. Virou a decisão D18.

**Catálogo piscando a cada volta.**
Notei que voltar ao catálogo recarregava tudo, e perguntei se não faltava cache. Faltava menos do que parecia: a tela se apagava de propósito antes de buscar. Cache com prazo seria a solução errada, porque a resposta carrega a lotação das sessões e serví-la velha marcaria como disponível uma sessão esgotada. Ficou a última resposta mantida na tela enquanto a nova chega. Virou a decisão D19.

**Portaria não tinha como ser criada, e valia para o filme inteiro.**
Perguntei como se cria uma portaria para outro filme, e a resposta expôs duas falhas. A primeira: não havia como. O comentário no código prometia que o organizador criaria portarias, e essa rota nunca existiu — só o seed criava. A segunda apareceu ao destrinchar o vínculo: a portaria era amarrada ao filme, então aceitava ingresso de qualquer sessão dele, em qualquer horário e qualquer cinema. Alguém com ingresso das 22h entraria na sessão das 19h, sentaria na poltrona de outro comprador e ainda perderia a sessão que pagou, porque o ingresso queima na entrada errada.

O agente ofereceu três saídas e recomendou a mais barata — documentar o limite, ou conferir uma janela de horário eu escolhi trocar o modelo: a portaria passou a ser vinculada à exibição. A verificação depois mostrou que a janela de horário não teria bastado, porque o mesmo filme começa à mesma hora em dois cinemas do cenário semeado, e só o vínculo pela exibição fecha horário, sala e cinema juntos. Virou a decisão D21.

**Conta de portaria por sessão não fazia sentido.**
Apontei que criar e-mail e senha para cada exibição é insustentável: a conta morre com a sessão, alguém precisa inventar e distribuir credenciais toda noite, e senha que se multiplica acaba anotada num papel. Pedi que o agente pesquisasse como isso é feito de verdade. Ele voltou com um código de pareamento por dispositivo, e recusei: um código curto, feito para ser ditado por telefone, vaza — e quem o tiver valida ingresso dos outros, fazendo o titular legítimo levar "já utilizado". Propus contas de funcionário com permissão de portaria, ativando a sessão que vão atender. A pesquisa seguinte mostrou que é exatamente o padrão do mercado. Virou a decisão D24.

**Cidade e UF digitadas à mão quebravam o filtro.**
Notei que o cadastro de cinema pedia cidade e UF por escrito, e que isso permitiria "São Paulo" e "sao paulo" coexistirem — o filtro do catálogo agrupa por cidade, então viraria duas. Pedi a melhor implementação em vez de um remendo de normalização. Ficaram UF de uma constante e município do IBGE, com o código guardado: nome de cidade se repete entre estados, e agrupar por texto juntaria cidades sem relação. Virou a decisão D23.

**Não havia como criar um organizador.**
Cobrei que o sistema não tinha caminho para o primeiro organizador. Pedi as alternativas com prós e contras antes de escolher, e o argumento decisivo foi de ambiente: o plano gratuito do Render não dá shell, então um comando de linha resolveria só na máquina local. Escolhi o primeiro cadastro virar organizador, somado à promoção pelo painel. Virou a decisão D22.

**Conta de portaria era um posto, não uma pessoa.**
Depois de aceitar o modelo de funcionário escolhendo o turno, apontei que o vocabulário ainda estava errado: a conta se chamava "portaria", e enquanto se chamasse assim continuaria parecendo natural criar uma por sessão. Passou a ser conta de **funcionário**, que abre a portaria para trabalhar. E a promoção a organizador deixou de pedir e-mail digitado: virou uma lista de funcionários para escolher, porque digitar exige saber de cor o endereço e erra calado.

**Telas cortadas no celular.**
Abri a compra num aparelho de 360px e o mapa de assentos vazava pela direita, com o rótulo da trilha de compra cortado à esquerda. Pedi correção, zoom no mapa e uma barra fixa embaixo com poltronas escolhidas, total e o botão de seguir — mantendo o resumo completo no fim da página. A barra se apaga quando o resumo entra em cena, para não haver duas ações iguais na tela ao mesmo tempo.

**Painel do organizador amontoado.**
Cobrei que eventos, cinemas, salas, funcionários e organizadores ficavam empilhados numa tela só. Virou navegação por abas: as áreas são usadas em momentos diferentes, e rolar por três assuntos para chegar ao quarto era trabalho à toa.

**Faltava editar e remover cinema, sala e funcionário.**
Apontei que o cadastro só crescia: dava para criar, nunca corrigir nem apagar. Entraram edição e remoção nos três, com as recusas que fazem sentido — cinema com sala não sai, sala com sessão não sai, e funcionário que já validou ingresso não sai porque o histórico deixaria de dizer quem estava na porta. Virou a decisão D25.

**Coluna que respondia a pergunta errada.**
Perguntei o que era a coluna "atendendo agora" e por que existia. Ao explicar, ficou claro que ela responde "o que o João atende", enquanto quem opera um cinema pergunta o contrário: "a sessão das 21:30 tem alguém na porta?". Pedi para inverter. Entrou um bloco acima da tabela com as próximas sessões e quem cobre cada uma, destacando as descobertas. Virou a decisão D26.

**Catálogo repartido entre organizadores não fazia sentido.**
Cada organizador só via os próprios eventos e sessões. Apontei que queria tudo unificado. A mudança resolveu uma inconsistência que já existia: cinema nunca teve dono, então metade do cadastro era compartilhada e a outra metade não, sem nada justificando a linha entre elas. Virou a decisão D29.

**Organizador precisava validar ingresso.**
Pedi que o organizador pudesse abrir a portaria por qualquer motivo. O agente havia escrito o oposto no código — que acumular os papéis daria a quem opera a porta o poder de publicar — e o argumento não se aplicava: quem já pode tudo não ganha poder ao validar. Virou a decisão D27, junto com editar e revogar organizador.

**Poltronas somiam depois do login.**
Escolhi poltronas sem estar logado, fui mandado para o login e voltei com o mapa em branco. O comentário no código já prometia preservar a seleção — e nada preservava. Virou memória por sessão de cinema, com as poltronas que outra pessoa levou no meio-tempo saindo sozinhas.

**Mapa cortado em sala grande.**
Salas altas perdiam as fileiras de cima, sem jeito de alcançá-las. Pedi pesquisa antes da correção. O agente havia introduzido o defeito ao consertar outro corte, e propôs um botão de "ver a sala inteira"; preferi zoom de verdade — roda no computador, pinça no celular e uma barra ao lado. Virou a decisão D31.

**Rótulo da trilha no lugar errado no computador.**
A correção do celular tinha mudado os dois. Pedi que no computador o nome da etapa voltasse para baixo do ícone, mantendo o novo comportamento na tela estreita.

**Rascunho não se apagava, e o mesmo filme entrava duas vezes.**
Cobri as duas coisas. Ficou remoção só de rascunho sem sessões — publicado pode ter ingresso vendido — e recusa de filme repetido nomeando o evento que já existe. Virou a decisão D30.

**Protótipo de design versionado.**
Desenhei um protótipo da sala de cinema antes de a tela existir. A imagem entra no repositório como artefato de processo; o arquivo de edição fica de fora por peso.

**Campos do painel sem rótulo associado.**
Apareceu ao escrever o teste da busca de filme: o seletor por rótulo não encontrava o campo. Vinte e oito campos do painel usavam um `<span>` que parecia rótulo mas não estava ligado a nada, então leitor de tela anunciava campo sem nome. Trocados por `<label>`, sem mudança visual, já que o estilo era o mesmo.

**Encolher a sala passava por cima de ingresso vendido.**
Perguntei se travar a sala depois da primeira venda não deixaria algum buraco. Deixava, e não onde eu imaginava: a regra existente cobria trocar a sala de uma exibição, mas não mexer nas dimensões da própria sala. Reproduzido contra a API, uma sala 8x12 com a poltrona H12 vendida aceitava virar 3x4, e o cliente ficava com ingresso de uma fileira que o cadastro passou a negar. Virou a decisão D35.

**A tela de pagamento recusado mentia sobre as poltronas.**
Apareceu ao escrever os testes de front: a tela dizia "as poltronas voltaram para o mapa", e a D13 estabelece o contrário, que elas seguem reservadas para quem quiser tentar outro cartão. Conferido contra a API, a poltrona continua ocupada. O texto mandava o cliente reescolher o que ainda era dele.

**Revogar organizador devolvia a conta a cliente.**
Pedi que revogar o papel devolvesse a pessoa a funcionário, e não a cliente. O agente havia tratado a revogação como se o papel anterior não importasse. Ao destrinchar, o defeito era maior do que o incômodo que me fez pedir: como a criação de funcionário recusa e-mail já cadastrado e não há recuperação de senha no escopo, quem subisse e descesse ficava com o e-mail queimado e sem caminho de volta. Uma operação e a sua inversa precisam se cancelar. Virou a decisão D32.

**O botão "validar outro" sumia sob o mouse.**
Percebi que a opção desaparecia justamente ao apontar para ela. O hover invertia as cores usando `currentColor` no fundo e trocando o texto na mesma regra — mas `currentColor` resolve contra a cor já computada do próprio elemento, então fundo e texto caíam na mesma cor, e o botão virava um retângulo invisível sobre o veredito. O comentário no código previa o risco e a correção não funcionava. Agora cada desfecho declara as duas cores.

**Organizador de plantão aparecia como porta descoberta.**
Depois de liberar a portaria para o organizador, notei que colocá-lo numa sessão não o mostrava alocado em lugar nenhum. A consulta da cobertura filtrava só quem tem o papel de portaria, então a sessão que ele estava atendendo continuava em carmim, como se ninguém estivesse lá — a lista que existe para responder "esta porta tem alguém" errava justamente sobre quem lê a tela. Virou a decisão D33.

**A portaria só aparecia para quem tinha o papel de portaria.**
Pedi que o organizador também pudesse abrir a tela da portaria e validar QR. A permissão já existia na API desde a D27 — o organizador enxerga todas as sessões e a validação nunca exigiu o papel de portaria —, mas a navegação mostrava o elo só para funcionários e a tela recusava a entrada. Permissão sem caminho na interface é permissão que não existe.

## Ajustes surgidos na verificação

**`passlib` e `python-jose` trocados por `bcrypt` e `PyJWT`.**
A lista inicial de dependências usava as duas primeiras. Um teste de instalação revelou que `passlib 1.7.4` quebra com `bcrypt 5.x` — lê um atributo interno removido na versão 4.1. As bibliotecas diretas resolvem o problema e ainda eliminam duas dependências.

**Ambiente corrigido antes da primeira linha.**
O Python instalado era 32-bit numa máquina 64-bit. Pacotes como `psycopg` e `pydantic-core` não distribuem versão compilada para essa combinação, e a instalação falharia tentando compilar do zero. Detectado antes de escrever código.

**Migrations revisadas antes de aplicar.**
O `--autogenerate` do Alembic nomeou uma chave estrangeira como `None`, o que quebraria o `downgrade`. Corrigido à mão nas duas migrations em que ocorreu.

**Três "bugs" que eram ambiente, não código.**
Num mesmo dia: a API servindo um contrato antigo porque fora subida sem recarga; o `tsc --noEmit` passando onde `npm run build` falhava, por não aplicar o `tsconfig` do projeto; e vários servidores dividindo a porta 8000, porque `uvicorn --reload` encerrado à força deixa processos filhos vivos herdando o socket. Nos três casos o sintoma apontava para o código, e a causa era ter verificado contra um substituto conveniente. Deu origem ao `api/dev.py`, que recusa subir com a porta ocupada, e à seção de verificação do `CLAUDE.md`.

Voltou a acontecer horas depois, agora como um `NaN/undefined` na ocupação das sessões: um campo novo no schema, um servidor que subira antes dele. O `dev.py` evita o caso pior — servidores concorrentes na mesma porta — mas não obriga ninguém a reiniciar depois de editar. A regra virou explícita no `CLAUDE.md`: alteração em `models.py` ou `schemas.py` só está verificada depois de a API reiniciar e o `/openapi.json` servido confirmar o campo.

**Limite de tentativas recalibrado.**
O primeiro valor era 10 logins por IP a cada 5 minutos. Os testes começaram a falhar por esbarrar nele — que é exatamente o que aconteceria com usuários reais atrás de um IP compartilhado de escritório ou operadora móvel. O limite por IP subiu para 60; a defesa contra força bruta ficou na janela por conta, que independe de origem.

## O que foi feito sem IA

A escolha da stack, do escopo de reserva, da direção visual e do nome do produto. A decisão de usar TMDb com mapa de assentos em vez de pista por quantidade. E a leitura crítica de cada explicação antes de aceitar o código — de onde saíram as mudanças listadas acima.

---

*Atualizado ao longo do desenvolvimento.*
