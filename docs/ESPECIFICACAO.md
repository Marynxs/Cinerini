# Especificação

## Problema

Um organizador precisa publicar sessões de cinema e vender lugares numerados. Um cliente precisa escolher a poltrona, pagar e receber um comprovante que a portaria consiga validar na entrada — uma vez só, na sessão certa.

O ponto difícil não é o cadastro nem o pagamento: é que **o mesmo lugar não pode ser vendido duas vezes** e **o mesmo ingresso não pode entrar duas vezes**, mesmo com pessoas agindo no mesmo instante.

## Papéis

| Papel | Pode |
|---|---|
| **Organizador** | Buscar filmes no TMDb, criar eventos e sessões, definir sala, horário, preço e capacidade, publicar, acompanhar vendas, e validar na portaria como o funcionário faz |
| **Cliente** | Navegar e buscar sessões publicadas por cidade, cinema, data e título, escolher poltrona, pagar, ver seus ingressos, compartilhar um ingresso por link |
| **Funcionário** | Abrir a portaria, escolher a sessão do turno entre as do seu cinema e validar os ingressos dela, por câmera ou digitação |

A conta é de um funcionário e pertence a um cinema; quem a cria é o organizador. Portaria é a tela que ele abre para trabalhar, não a identidade da conta. A sessão do turno é escolhida pelo próprio funcionário, entre as daquele cinema (D24). É essa vinculação que permite responder "outra sessão" ou "outro evento" em vez de "inválido".

O primeiro cadastro numa instalação vazia nasce organizador; depois disso, um organizador promove um funcionário existente, escolhido em lista. Quem é promovido deixa de ser funcionário — os papéis são exclusivos (D22) — e revogar o papel devolve a conta à equipe, sem cinema definido (D32).

## Fluxos

### Publicação
Organizador busca no TMDb → escolhe o filme → o sistema importa título, sinopse, pôster e duração → organizador escolhe a sala e define horário e preço → publica. A publicação gera os assentos a partir do layout da sala.

Cinemas e salas são cadastrados uma vez e reaproveitados por qualquer exibição: o cinema guarda nome, cidade, estado e endereço; a sala guarda nome e dimensões.

Cidade e UF são escolhidas em lista, nunca digitadas — a UF de uma constante, o município do IBGE — e o cadastro guarda o código do município. Sem isso o filtro do catálogo agrupa por texto, e duas grafias da mesma cidade viram duas cidades (D23).

### Compra
Cliente abre a sessão → vê o mapa com assentos livres, ocupados e em espera → escolhe → o assento entra em espera por 10 minutos → paga → o ingresso é emitido com código assinado.

Se o pagamento for recusado, o pedido fica recusado mas continua pagável, e as poltronas seguem reservadas até a espera vencer — quem errou um dígito tenta outro cartão sem perder a escolha (D13). Se o cliente abandonar, a espera expira e o assento volta sozinho.

### Validação
Cada portaria atende **uma exibição** — aquele filme, naquele horário, naquela sala (D21). Aponta a câmera para o QR, ou digita o código, e o sistema responde com um de seis estados:

| Estado | Quando | Mostra também |
|---|---|---|
| **Válido** | Assinatura confere, exibição confere, ainda não usado | Poltrona, cliente e a sessão |
| **Inválido** | Assinatura não confere ou código inexistente | — |
| **Já utilizado** | Ingresso legítimo, já validado antes | Horário da validação anterior |
| **Outra sessão** | Mesmo filme, exibição diferente | Para qual sessão o ingresso vale |
| **Outro evento** | Ingresso legítimo, de outro filme | Qual é o filme correto |
| **Cancelado** | Ingresso legítimo, reembolsado antes da sessão | Poltrona e nome do cliente |

Os dois recusados por encaminhamento são separados porque a reação de quem opera é diferente: um manda a pessoa para outra sala, o outro para outro horário. Nenhum dos dois consome o ingresso — a portaria certa ainda precisa aceitá-lo.

O ingresso é marcado como usado no mesmo passo em que é validado.

Ao entrar, a portaria escolhe qual sessão está atendendo, e pode trocar a qualquer momento — é o gesto da virada de uma exibição para a seguinte, e não depende do organizador. O cadastro público nunca concede o papel: ele decide quem entra na sala.

### Compartilhamento
Cliente gera um link para um ingresso. Quem abre vê o ingresso e o QR. O link é revogável, e revogá-lo não invalida o ingresso.

## Regras de negócio

1. Um assento pertence a uma sessão e não pode ter dois ingressos não cancelados.
2. Ingresso em espera ocupa o assento. Espera dura 10 minutos.
3. Pagamento recusado não libera os assentos: a reserva vale até a espera vencer, e o pedido continua pagável (D13).
4. Cancelamento devolve o assento ao estoque.
5. Ingresso usado não volta a ser válido.
6. Só sessões publicadas aparecem para o cliente.
7. Valores em centavos.

## Pagamento simulado

Sem transação financeira real. O desfecho é determinístico para que ambos os caminhos sejam demonstráveis: **cartão terminado em `0` é recusado**, os demais são aprovados.

## Dados semeados

Um organizador, dois clientes, uma conta de portaria já ligada a um cinema mas **sem turno escolhido**, e sessões publicadas com assentos disponíveis. O fluxo inteiro é percorrível sem cadastrar nada; escolher o turno é o primeiro gesto de quem abre a portaria, e deixá-lo pronto esconderia o passo.

## Critérios de aceite

Duas colunas porque o comportamento pode estar correto na API antes de existir tela para ele. Um critério só está cumprido quando as duas marcam.

| Critério | API | Tela |
|---|:-:|:-:|
| Cliente conclui compra e recebe ingresso com QR | ✅ | ✅ |
| Dois clientes disputando o mesmo assento: um conclui, o outro recebe recusa clara | ✅ | ✅ |
| Pagamento recusado permite nova tentativa, e a espera libera o assento no vencimento | ✅ | ✅ |
| Link compartilhado exibe o ingresso; revogado deixa de exibir | ✅ | ✅ |
| Portaria retorna os quatro estados exigidos corretamente | ✅ | ✅ |
| Mesmo ingresso validado duas vezes retorna "já utilizado" na segunda | ✅ | ✅ |
| Ingresso de outro evento retorna "outro evento", não "inválido" | ✅ | ✅ |
| QR com assinatura adulterada retorna "inválido" | ✅ | ✅ |
| Banco reproduzível do zero por migration e seed | ✅ | — |

A portaria devolve seis estados, dois a mais que os quatro exigidos. O ingresso cancelado se distingue do inválido, e "outra sessão" se distingue de "outro evento", pela mesma razão: ingresso legítimo recusado não é ingresso falso, e a reação de quem opera muda em cada caso (D16, D21).

## Fora de escopo

Nota fiscal, revenda entre usuários, aplicativo nativo, recuperação de senha, envio por e-mail. Pista por quantidade não é implementada — o desafio pede um dos dois modos, e a escolha foi mapa de assentos.
