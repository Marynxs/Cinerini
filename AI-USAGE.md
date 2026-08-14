# Uso de IA

## Ferramenta

Claude Code (Opus 5), em sessão única e contínua, conduzida por prompt no terminal.

## Como foi conduzida

O enunciado **não** foi colado na ferramenta pedindo a aplicação pronta. A condução seguiu uma ordem deliberada:

1. **Leitura e estratégia antes de código.** A primeira tarefa dada à ferramenta foi analisar o enunciado e propor o que priorizar, não implementar. O resultado foi um plano de sete dias com uma regra de corte definida: o fluxo completo precisa rodar antes de qualquer polimento.
2. **Decisões de produto tomadas por mim.** Stack, escopo de reserva, direção visual e nome foram escolhas minhas. Em ao menos um caso — a personalidade tipográfica — escolhi contra a recomendação da ferramenta.
3. **Identidade visual decidida por comparação.** Três direções foram prototipadas lado a lado antes de qualquer tela real ser construída, e a escolhida foi travada em tokens no `CLAUDE.md` antes do primeiro componente.
4. **Explicação exigida a cada bloco.** Cada peça foi explicada antes de ser aceita. Onde a explicação não convenceu, o código mudou.

## Artefatos de condução

- `CLAUDE.md` — arquivo de contexto que orienta a ferramenta: garantias inegociáveis, tokens visuais, convenções. É o que impede a IA de reintroduzir soluções já descartadas.
- `docs/ESPECIFICACAO.md` — o que o sistema faz, escrito antes da implementação.
- `docs/DECISOES.md` — registro cronológico com o que foi descartado e por quê.

## Correções feitas sobre a saída da ferramenta

Registro dos pontos em que a primeira proposta foi rejeitada ou corrigida:

- **`passlib` + `python-jose` descartados.** Uma verificação de instalação revelou que `passlib 1.7.4` quebra com `bcrypt 5.x`. Trocado por `bcrypt` e `PyJWT` diretos.
- **Ressalva sobre monoespaçado revista.** A ferramenta desaconselhou mono no painel do organizador; a objeção estava mal calibrada, já que mono alinha dado tabular melhor que proporcional. Mantido mono, com exceção só para prosa.
- **Ambiente corrigido antes do código.** Python 32-bit em máquina 64-bit teria quebrado na instalação do driver do Postgres. Detectado e corrigido no dia 1.
- **Sala normalizada por questionamento na revisão.** O modelo entregue trazia sala e dimensões como campos soltos em `Showing`. Ao revisar linha a linha, questionei se sala não deveria ser tabela própria. A ferramenta havia argumentado contra, por escopo; mantive a posição, e ao detalhar o raciocínio ficou claro que aqueles campos viravam dado morto após a geração dos assentos. O modelo mudou (decisão D6), com migration nova em vez de reescrita da original.
- **Migration gerada foi lida antes de aplicada.** O autogenerate do Alembic propôs recriar uma chave estrangeira já existente e nomeou outra como `None`, o que quebraria o `downgrade`. Ambas corrigidas à mão, e o ciclo upgrade/downgrade/upgrade verificado.

## O que foi feito sem IA

Escolha da stack, do escopo de reserva, da direção visual e do nome do produto. A decisão de usar TMDb com mapa de assentos em vez de pista por quantidade. A leitura crítica de cada explicação antes de aceitar o código.

---

*Documento atualizado ao longo do desenvolvimento.*
