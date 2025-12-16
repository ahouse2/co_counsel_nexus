import { useEffect, useRef, useState } from 'react';
import { Mic, Square, Loader2, Volume2, User } from 'lucide-react';
import { useVoiceSession } from '../../hooks/useVoiceSession';
import { Canvas } from '@react-three/fiber';
import { Avatar3D } from '../avatar/Avatar3D';

interface VoiceConsoleProps {
    caseId: string;
    personaId?: string;
}

export function VoiceConsole({ caseId, personaId = 'default' }: VoiceConsoleProps) {
    const { state, startListening, stopListening, cancel, analyser } = useVoiceSession(caseId, personaId);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [showAvatar, setShowAvatar] = useState(true);

    // Visualize audio level (2D fallback)
    useEffect(() => {
        if (showAvatar) return;
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const centerY = canvas.height / 2;
            ctx.beginPath();
            ctx.moveTo(0, centerY);

            const amplitude = (state.audioLevel / 255) * (canvas.height / 2);

            for (let x = 0; x < canvas.width; x++) {
                const frequency = 0.1;
                const phase = Date.now() * 0.01;
                const y = centerY + Math.sin(x * frequency + phase) * amplitude * Math.sin(x / canvas.width * Math.PI);
                ctx.lineTo(x, y);
            }

            ctx.strokeStyle = state.status === 'listening' ? '#00f0ff' :
                state.status === 'speaking' ? '#00ff9d' :
                    state.status === 'processing' ? '#fbbf24' : '#334155';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.shadowBlur = 10;
            ctx.shadowColor = ctx.strokeStyle;

            requestAnimationFrame(draw);
        };

        const animationId = requestAnimationFrame(draw);
        return () => cancelAnimationFrame(animationId);
    }, [state.audioLevel, state.status, showAvatar]);

    return (
        <div className="bg-black/80 border border-halo-border rounded-xl p-6 backdrop-blur-md w-full max-w-md mx-auto shadow-[0_0_30px_rgba(0,0,0,0.5)]">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${state.status === 'listening' ? 'bg-red-500 animate-pulse' :
                        state.status === 'speaking' ? 'bg-green-500' :
                            state.status === 'processing' ? 'bg-yellow-500 animate-bounce' :
                                'bg-slate-500'
                        }`} />
                    <span className="text-xs font-mono uppercase tracking-widest text-halo-muted">
                        {state.status === 'idle' ? 'Voice Interface Ready' :
                            state.status === 'listening' ? 'Listening...' :
                                state.status === 'processing' ? 'Processing...' :
                                    state.status === 'speaking' ? 'Speaking...' : 'Error'}
                    </span>
                </div>
                <button
                    onClick={() => setShowAvatar(!showAvatar)}
                    className={`p-1 rounded hover:bg-white/10 ${showAvatar ? 'text-halo-cyan' : 'text-halo-muted'}`}
                    title="Toggle Avatar"
                >
                    <User size={16} />
                </button>
            </div>

            {/* Visualization / Avatar */}
            <div className="bg-black/50 rounded-lg border border-white/5 h-64 mb-6 relative overflow-hidden">
                {showAvatar ? (
                    <Canvas camera={{ position: [0, 0, 1.5], fov: 50 }}>
                        <Avatar3D
                            url="https://models.readyplayer.me/64b7a85628462f4923495031.glb"
                            isSpeaking={state.status === 'speaking'}
                            analyser={analyser}
                        />
                    </Canvas>
                ) : (
                    <div className="w-full h-full relative">
                        <canvas
                            ref={canvasRef}
                            width={400}
                            height={256}
                            className="w-full h-full"
                        />
                        {/* Overlay Icon */}
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
                            {state.status === 'listening' && <Mic size={48} className="text-halo-cyan" />}
                            {state.status === 'speaking' && <Volume2 size={48} className="text-green-500" />}
                            {state.status === 'processing' && <Loader2 size={48} className="text-yellow-500 animate-spin" />}
                        </div>
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex justify-center gap-4">
                {state.status === 'idle' || state.status === 'error' ? (
                    <button
                        onClick={startListening}
                        className="w-16 h-16 rounded-full bg-halo-cyan/10 border border-halo-cyan text-halo-cyan flex items-center justify-center hover:bg-halo-cyan/20 hover:scale-105 transition-all shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                        aria-label="Start Listening"
                    >
                        <Mic size={24} />
                    </button>
                ) : (
                    <button
                        onClick={state.status === 'listening' ? stopListening : cancel}
                        className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500 text-red-500 flex items-center justify-center hover:bg-red-500/20 hover:scale-105 transition-all shadow-[0_0_20px_rgba(239,68,68,0.2)]"
                        aria-label="Stop Listening"
                    >
                        <Square size={24} fill="currentColor" />
                    </button>
                )}
            </div>

            <div className="text-center mt-4 text-[10px] text-halo-muted uppercase tracking-wider">
                {state.status === 'listening' ? 'Tap to Stop' : 'Tap to Speak'}
            </div>
        </div>
    );
}
