/* Leitura de QR pela câmera.

   Usa o jsQR e não o `BarcodeDetector` nativo do navegador: nenhum navegador
   de iPhone implementa a API — todos usam o WebKit, e a Apple a mantém
   desligada. Numa portaria, o aparelho mais provável na mão de quem valida é
   justamente um celular, e um caminho que falha em metade deles não é
   caminho (D20).

   A decodificação roda no thread principal, a cada 150 ms, sobre um quadro
   reduzido. Cabe folgado no orçamento: o trabalho é uma imagem pequena a
   cada sexto de segundo, não um vídeo inteiro.
*/

import jsQR from 'jsqr';
import { useCallback, useEffect, useRef, useState } from 'react';

/** Intervalo entre tentativas de leitura. Abaixo disso o ganho é
    imperceptível para quem está mirando, e o custo em CPU é real num
    celular modesto. */
const INTERVALO_MS = 150;

/** Lado máximo do quadro analisado. O QR de um ingresso ocupa boa parte da
    tela do celular que o exibe, e reduzir corta o custo da decodificação
    sem tirar legibilidade do código. */
const LADO_MAXIMO = 640;

export type EstadoCamera = 'iniciando' | 'lendo' | 'negada' | 'ausente' | 'falhou';

interface Retorno {
  video: React.RefObject<HTMLVideoElement | null>;
  estado: EstadoCamera;
  reiniciar: () => void;
}

/**
 * Liga a câmera e chama `aoLer` quando encontra um QR.
 *
 * Enquanto `ativo` for falso a câmera é desligada de verdade — não basta
 * parar de decodificar, porque o indicador de gravação continuaria aceso e
 * a bateria continuaria sendo gasta.
 */
export function useLeitorQr(ativo: boolean, aoLer: (texto: string) => void): Retorno {
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const [estado, setEstado] = useState<EstadoCamera>('iniciando');
  const [tentativa, setTentativa] = useState(0);

  // A função de leitura muda a cada render da tela, mas o laço da câmera não
  // deve ser remontado por isso — remontar reabriria o fluxo de vídeo e
  // piscaria a imagem a cada quadro lido.
  const leitor = useRef(aoLer);
  leitor.current = aoLer;

  const reiniciar = useCallback(() => setTentativa((n) => n + 1), []);

  useEffect(() => {
    if (!ativo) return;

    let fluxo: MediaStream | null = null;
    let timer: number | undefined;
    let encerrado = false;

    // Guardado aqui e não lido do ref na limpeza: quando o efeito é
    // desfeito, o ref já pode apontar para outro elemento ou para nada, e o
    // fluxo precisa ser solto exatamente de onde foi preso.
    let preso: HTMLVideoElement | null = null;

    async function ligar() {
      if (!navigator.mediaDevices?.getUserMedia) {
        // Sem HTTPS o navegador nem expõe a API. Vale dizer "ausente" e
        // deixar a digitação manual assumir.
        setEstado('ausente');
        return;
      }

      try {
        fluxo = await navigator.mediaDevices.getUserMedia({
          // A traseira é a que aponta para o ingresso de outra pessoa.
          video: { facingMode: 'environment' },
        });
      } catch (e) {
        if (encerrado) return;
        const nome = (e as DOMException).name;
        setEstado(nome === 'NotAllowedError' ? 'negada'
          : nome === 'NotFoundError' ? 'ausente' : 'falhou');
        return;
      }

      if (encerrado) {
        fluxo.getTracks().forEach((t) => t.stop());
        return;
      }

      const elemento = video.current;
      if (!elemento) return;

      preso = elemento;
      elemento.srcObject = fluxo;
      // O iOS recusa reproduzir sem gesto do usuário quando o vídeo não é
      // mudo e embutido; os dois atributos estão no JSX, aqui só resta
      // tolerar a recusa sem derrubar a tela.
      await elemento.play().catch(() => {});

      setEstado('lendo');
      timer = window.setInterval(procurar, INTERVALO_MS);
    }

    function procurar() {
      const elemento = video.current;
      if (!elemento || elemento.readyState < elemento.HAVE_CURRENT_DATA) return;

      const escala = Math.min(
        1, LADO_MAXIMO / Math.max(elemento.videoWidth, elemento.videoHeight));
      const largura = Math.round(elemento.videoWidth * escala);
      const altura = Math.round(elemento.videoHeight * escala);
      if (largura === 0 || altura === 0) return;

      canvas.current ??= document.createElement('canvas');
      const tela = canvas.current;
      tela.width = largura;
      tela.height = altura;

      // `willReadFrequently` evita que o navegador mantenha o canvas na GPU:
      // sem isso, cada `getImageData` paga uma cópia de volta para a memória
      // principal, seis vezes por segundo.
      const ctx = tela.getContext('2d', { willReadFrequently: true });
      if (!ctx) return;

      ctx.drawImage(elemento, 0, 0, largura, altura);
      const quadro = ctx.getImageData(0, 0, largura, altura);

      const achado = jsQR(quadro.data, largura, altura, {
        inversionAttempts: 'dontInvert',
      });

      if (achado?.data) leitor.current(achado.data);
    }

    ligar();

    return () => {
      encerrado = true;
      if (timer) clearInterval(timer);
      fluxo?.getTracks().forEach((t) => t.stop());
      if (preso) preso.srcObject = null;
    };
  }, [ativo, tentativa]);

  useEffect(() => {
    if (!ativo) setEstado('iniciando');
  }, [ativo]);

  return { video, estado, reiniciar };
}
