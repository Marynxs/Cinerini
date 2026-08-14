# Especificação

## Problema

Um organizador precisa publicar sessões de cinema e vender lugares numerados. Um cliente precisa escolher a poltrona, pagar e receber um comprovante que a portaria consiga validar na entrada — uma vez só, no evento certo.

O ponto difícil não é o cadastro nem o pagamento: é que **o mesmo lugar não pode ser vendido duas vezes** e **o mesmo ingresso não pode entrar duas vezes**, mesmo com pessoas agindo no mesmo instante.

## Papéis

| Papel | Pode |
|---|---|
| **Organizador** | Buscar filmes no TMDb, criar eventos e sessões, definir sala, horário, preço e capacidade, publicar, acompanhar vendas |
| **Cliente** | Navegar e buscar sessões publicadas, escolher poltrona, pagar, ver seus ingressos, compartilhar um ingresso por link |
| **Portaria** | Validar ingressos de **um evento específico**, por câmera ou digitação |

Portaria é vinculada a um evento. É essa vinculação que permite responder "evento errado" em vez de "inválido".

## Fluxos

### Publicação
Organizador busca no TMDb → escolhe o filme → o sistema importa título, sinopse, pôster e duração → organizador escolhe a sala e define horário e preço → publica. A publicação gera os assentos a partir do layout da sala.

Salas são cadastradas uma vez, com local, nome e dimensões, e reaproveitadas por qualquer exibição.

### Compra
Cliente abre a sessão → vê o mapa com assentos livres, ocupados e em espera → escolhe → o assento entra em espera por 10 minutos → paga → o ingresso é emitido com código assinado.

Se o pagamento for recusado, o assento volta ao estoque imediatamente. Se o cliente abandonar, a espera expira e o assento volta sozinho.

### Validação
Portaria aponta a câmera para o QR, ou digita o código. O sistema responde com um de quatro estados:

| Estado | Quando | Mostra também |
|---|---|---|
| **Válido** | Assinatura confere, evento confere, ainda não usado | Poltrona e nome do cliente |
| **Inválido** | Assinatura não confere ou código inexistente | — |
| **Já utilizado** | Ingresso legítimo, já validado antes | Horário da validação anterior |
| **Outro evento** | Ingresso legítimo, de evento diferente | Qual é o evento correto |

O ingresso é marcado como usado no mesmo passo em que é validado.

### Compartilhamento
Cliente gera um link para um ingresso. Quem abre vê o ingresso e o QR. O link é revogável, e revogá-lo não invalida o ingresso.

## Regras de negócio

1. Um assento pertence a uma sessão e não pode ter dois ingressos não-cancelados.
2. Ingresso em espera ocupa o assento. Espera dura 10 minutos.
3. Pagamento recusado cancela o pedido e libera os assentos.
4. Cancelamento devolve o assento ao estoque.
5. Ingresso usado não volta a ser válido.
6. Só sessões publicadas aparecem para o cliente.
7. Valores em centavos.

## Pagamento simulado

Sem transação financeira real. O desfecho é determinístico para que ambos os caminhos sejam demonstráveis: **cartão terminado em `0` é recusado**, os demais são aprovados.

## Dados semeados

Um organizador, dois clientes, um usuário de portaria e ao menos uma sessão publicada com assentos disponíveis — o fluxo inteiro percorrível sem cadastrar nada.

## Critérios de aceite

- [ ] Cliente conclui compra e recebe ingresso com QR
- [ ] Dois clientes disputando o mesmo assento: um conclui, o outro recebe recusa clara
- [ ] Pagamento recusado libera o assento
- [ ] Portaria retorna os quatro estados corretamente
- [ ] Mesmo ingresso validado duas vezes retorna "já utilizado" na segunda
- [ ] Ingresso de outro evento retorna "outro evento", não "inválido"
- [ ] QR com assinatura adulterada retorna "inválido"
- [ ] Link compartilhado exibe o ingresso; revogado deixa de exibir
- [ ] Banco reproduzível do zero por migration e seed

## Fora de escopo

Nota fiscal, revenda entre usuários, aplicativo nativo, recuperação de senha, envio por e-mail. Pista por quantidade não é implementada — o desafio pede um dos dois modos, e a escolha foi mapa de assentos.
