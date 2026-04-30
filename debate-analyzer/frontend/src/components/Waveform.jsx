import { useEffect, useRef } from 'react';

export function Waveform({ analyserNode, isRecording }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (!analyserNode || !isRecording) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw);
      analyserNode.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = canvas.width / bufferLength * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        const intensity = dataArray[i] / 255;
        ctx.fillStyle = `rgba(29, 158, 117, ${0.4 + intensity * 0.6})`; // teal
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);
        x += barWidth;
      }
    };
    draw();

    return () => cancelAnimationFrame(rafRef.current);
  }, [analyserNode, isRecording]);

  return (
    <canvas
      ref={canvasRef}
      width={480}
      height={80}
      className="w-full max-w-lg h-20 rounded-lg bg-white/50 backdrop-blur-sm border border-white/20 shadow-inner"
    />
  );
}
