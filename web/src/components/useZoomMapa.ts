/* Zoom e deslocamento do mapa de assentos.

   Três entradas para a mesma coisa, porque três contextos diferentes:
   roda do mouse no computador, pinça no celular, e uma barra deslizante
   para quem prefere um controle visível a um gesto.

   O que isto assume, e é decisão consciente: sobre o mapa, a roda deixa de
   rolar e passa a ampliar. A literatura de gráficos interativos alerta que
   isso atrapalha rolar a página, e a mitigação comum é exigir Ctrl. Aqui a
   troca é aceita porque o mapa vive numa tela que não rola no computador, e
   porque arrastar assume o papel de mover — nenhuma parte fica inalcançável
   (D31).
*/

import { useCallback, useEffect, useRef, useState } from 'react';

/** Lado da poltrona em pixels. O piso ainda deixa a sala legível; o teto é
    onde a poltrona para de parecer poltrona. */
export const ZOOM_MIN = 14;
export const ZOOM_MAX = 56;
export const ZOOM_PADRAO = 22;

const PASSO_RODA = 2;

const limitar = (v: number) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, v));

export function useZoomMapa() {
  const [lado, setLadoBruto] = useState(ZOOM_PADRAO);
  const rolagem = useRef<HTMLDivElement>(null);

  /* Ampliar em torno do centro do que está visível.

     Sem isto, ampliar joga a vista para o canto superior esquerdo e a
     pessoa perde a poltrona que estava olhando — que é exatamente a queixa
     que a literatura registra sobre zoom em plantas grandes. */
  const setLado = useCallback((proximo: number | ((l: number) => number)) => {
    setLadoBruto((atual) => {
      const novo = limitar(
        typeof proximo === 'function' ? proximo(atual) : proximo);
      const el = rolagem.current;

      if (el && novo !== atual) {
        const fator = novo / atual;
        const meioX = el.scrollLeft + el.clientWidth / 2;
        const meioY = el.scrollTop + el.clientHeight / 2;

        // Aplicado no quadro seguinte: o tamanho novo só existe depois de o
        // navegador repintar, e ler `scrollWidth` antes disso devolveria a
        // medida antiga.
        requestAnimationFrame(() => {
          el.scrollLeft = meioX * fator - el.clientWidth / 2;
          el.scrollTop = meioY * fator - el.clientHeight / 2;
        });
      }

      return novo;
    });
  }, []);

  // Roda do mouse. Registrado à mão porque o React trata `wheel` como
  // passivo, e listener passivo não pode chamar `preventDefault` — sem
  // isso a página rolaria junto com o zoom.
  useEffect(() => {
    const el = rolagem.current;
    if (!el) return;

    const aoGirar = (e: WheelEvent) => {
      e.preventDefault();
      setLado((l) => l - Math.sign(e.deltaY) * PASSO_RODA);
    };

    el.addEventListener('wheel', aoGirar, { passive: false });
    return () => el.removeEventListener('wheel', aoGirar);
  }, [setLado]);

  /* Pinça e arrasto, por Pointer Events.

     Um só conjunto de eventos cobre dedo, caneta e mouse — com `touch` e
     `mouse` separados seria preciso escrever a mesma lógica duas vezes e
     conciliar os eventos sintéticos que o navegador emite depois do toque. */
  const ativos = useRef(new Map<number, { x: number; y: number }>());
  const pinca = useRef<{ distancia: number; lado: number } | null>(null);
  const arrasto = useRef<{ x: number; y: number } | null>(null);

  const distancia = () => {
    const [a, b] = [...ativos.current.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  };

  const aoPressionar = (e: React.PointerEvent) => {
    ativos.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (ativos.current.size === 2) {
      pinca.current = { distancia: distancia(), lado };
      arrasto.current = null;
    } else if (ativos.current.size === 1 && e.pointerType !== 'mouse') {
      // Arrastar move o mapa só no toque. No mouse, arrastar sobre uma
      // poltrona seria confundido com a intenção de escolhê-la.
      arrasto.current = { x: e.clientX, y: e.clientY };
    }
  };

  const aoMover = (e: React.PointerEvent) => {
    if (!ativos.current.has(e.pointerId)) return;
    ativos.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (ativos.current.size === 2 && pinca.current) {
      const agora = distancia();
      if (pinca.current.distancia > 0) {
        setLado(pinca.current.lado * (agora / pinca.current.distancia));
      }
      return;
    }

    const el = rolagem.current;
    if (arrasto.current && el) {
      el.scrollLeft -= e.clientX - arrasto.current.x;
      el.scrollTop -= e.clientY - arrasto.current.y;
      arrasto.current = { x: e.clientX, y: e.clientY };
    }
  };

  const aoSoltar = (e: React.PointerEvent) => {
    ativos.current.delete(e.pointerId);
    if (ativos.current.size < 2) pinca.current = null;
    if (ativos.current.size === 0) arrasto.current = null;
  };

  return {
    lado,
    setLado,
    rolagem,
    gestos: {
      onPointerDown: aoPressionar,
      onPointerMove: aoMover,
      onPointerUp: aoSoltar,
      onPointerCancel: aoSoltar,
      onPointerLeave: aoSoltar,
    },
  };
}
