import './SeatMap.css';

export type SeatKind = 'standard' | 'accessible';

export interface Seat {
  id: number;
  row_label: string;
  number: number;
  kind: SeatKind;
  label: string;
  taken: boolean;
}

interface Props {
  seats: Seat[];
  selected: number[];
  onToggle: (seatId: number) => void;
  disabled?: boolean;
}

/** Símbolo internacional de acesso, simplificado para caber em 20px. */
function SimboloAcessivel() {
  return (
    <svg className="assento-simbolo" viewBox="0 0 24 24" aria-hidden="true"
         fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="4" r="2" fill="currentColor" stroke="none" />
      <path d="M10 8v6h5l3 5" />
      <path d="M14.5 14a5.5 5.5 0 1 1-6-4.9" />
    </svg>
  );
}

function agruparPorFileira(seats: Seat[]): [string, Seat[]][] {
  const fileiras = new Map<string, Seat[]>();

  for (const assento of seats) {
    const atual = fileiras.get(assento.row_label) ?? [];
    atual.push(assento);
    fileiras.set(assento.row_label, atual);
  }

  return [...fileiras.entries()]
    .map(([letra, lista]) =>
      [letra, lista.sort((x, y) => x.number - y.number)] as [string, Seat[]])
    // Ordem decrescente: a fileira A fica embaixo, encostada na tela.
    .sort(([a], [b]) => b.localeCompare(a));
}

export function SeatMap({ seats, selected, onToggle, disabled }: Props) {
  const fileiras = agruparPorFileira(seats);
  const numeros = fileiras[0]?.[1].map((a) => a.number) ?? [];
  const corredorApos = Math.ceil(numeros.length / 2);

  return (
    <div className="mapa">
      <div className="mapa-grade">
        <div className="mapa-numeros" aria-hidden="true">
          <span className="mapa-fileira-letra" />
          {numeros.map((numero, indice) => (
            <span key={numero} style={{ display: 'contents' }}>
              <span className="mapa-numero">{numero}</span>
              {indice + 1 === corredorApos && <span className="mapa-corredor" />}
            </span>
          ))}
          <span className="mapa-fileira-letra" />
        </div>

        {fileiras.map(([letra, assentos]) => (
          <div className="mapa-fileira" key={letra}>
            <span className="mapa-fileira-letra" aria-hidden="true">{letra}</span>

            {assentos.map((assento, indice) => (
              <Poltrona
                key={assento.id}
                assento={assento}
                escolhido={selected.includes(assento.id)}
                onToggle={onToggle}
                disabled={disabled}
                corredorDepois={indice + 1 === corredorApos}
              />
            ))}

            <span className="mapa-fileira-letra" aria-hidden="true">{letra}</span>
          </div>
        ))}
      </div>

      <div className="mapa-tela">
        <div className="mapa-tela-faixa" />
        <div className="mapa-tela-rotulo">Tela</div>
      </div>

      <Legenda />
    </div>
  );
}

interface PoltronaProps {
  assento: Seat;
  escolhido: boolean;
  onToggle: (seatId: number) => void;
  disabled?: boolean;
  corredorDepois: boolean;
}

function Poltrona({
  assento, escolhido, onToggle, disabled, corredorDepois,
}: PoltronaProps) {
  const acessivel = assento.kind === 'accessible';

  const classes = [
    'assento',
    assento.taken && 'assento--ocupado',
    escolhido && 'assento--escolhido',
    acessivel && 'assento--acessivel',
  ].filter(Boolean).join(' ');

  // O rótulo lido em voz alta precisa carregar o estado: sem isso, quem não
  // enxerga o mapa ouve só "F7" e não sabe se pode escolher.
  const situacao = assento.taken ? 'ocupada'
    : escolhido ? 'selecionada' : 'livre';
  const tipo = acessivel ? ', acessível' : '';

  return (
    <>
      <button
        type="button"
        className={classes}
        onClick={() => onToggle(assento.id)}
        disabled={assento.taken || disabled}
        aria-pressed={escolhido}
        aria-label={`Poltrona ${assento.label}${tipo}, ${situacao}`}
        title={assento.label}
      >
        {escolhido
          ? <span className="assento-marca" />
          : acessivel && <SimboloAcessivel />}
      </button>
      {corredorDepois && <span className="mapa-corredor" aria-hidden="true" />}
    </>
  );
}

function Legenda() {
  return (
    <div className="mapa-legenda">
      <span className="mapa-legenda-item">
        <span className="assento" aria-hidden="true" /> Livre
      </span>
      <span className="mapa-legenda-item">
        <span className="assento assento--escolhido" aria-hidden="true">
          <span className="assento-marca" />
        </span> Sua
      </span>
      <span className="mapa-legenda-item">
        <span className="assento assento--ocupado" aria-hidden="true" /> Ocupada
      </span>
      <span className="mapa-legenda-item">
        <span className="assento assento--acessivel" aria-hidden="true">
          <SimboloAcessivel />
        </span> Acessível
      </span>
    </div>
  );
}
