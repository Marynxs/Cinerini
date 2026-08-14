# Registro de decisões

Ordem cronológica. Cada entrada registra o que foi decidido, o que foi descartado e por quê.

---

## D1 · Catálogo externo: TMDb em vez de Ticketmaster

**Decidido:** TMDb como fonte do catálogo, modelando o domínio como cinema.

**Descartado:** Ticketmaster Discovery. A API é mais rica em dados de venue reais, mas o fluxo que ela sugere — shows com pista e setores — se resolve por quantidade de ingressos, não por assento.

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

**Onde a normalização para:** o local continua texto, não tabela. Neste escopo o cinema não tem atributo além do nome, e uma tabela de campo único não carrega informação que o texto já não carregue — custaria mais um CRUD no painel do organizador sem nada em troca.
