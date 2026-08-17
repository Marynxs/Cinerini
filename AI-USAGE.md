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

**Protótipo de design versionado.**
Desenhei um protótipo da sala de cinema antes de a tela existir. A imagem entra no repositório como artefato de processo; o arquivo de edição fica de fora por peso.

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
