import { useState } from 'react';
import { ShieldAlert, Gavel, Flame, AlertTriangle, BrainCircuit } from 'lucide-react';
import { endpoints } from '../../services/api';

interface ChallengeResult {
    weaknesses: { point: string; explanation: string }[];
    counter_arguments: { argument: string; evidence_cited: string }[];
    cross_examination: string[];
    overall_assessment: string;
}

export function AdversarialModule() {
    const [theory, setTheory] = useState('');
    const [result, setResult] = useState<ChallengeResult | null>(null);
    const [loading, setLoading] = useState(false);

    const handleChallenge = async () => {
        if (!theory.trim()) return;
        setLoading(true);
        try {
            const response = await endpoints.adversarial.challenge('default_case', theory);
            setResult(response.data);
        } catch (error) {
            console.error("Failed to challenge theory:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden relative bg-gradient-to-br from-black via-[#1a0505] to-black">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                    <Flame className="text-red-500 w-8 h-8 animate-pulse" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-red-100 uppercase tracking-wider">The Devil's Advocate</h2>
                    <p className="text-red-400/60 text-sm">Adversarial Strategy Simulator & Stress Test</p>
                </div>
            </div>

            <div className="flex-1 flex gap-8 overflow-hidden">
                {/* Input Column */}
                <div className="w-1/3 flex flex-col gap-4">
                    <div className="halo-card flex-1 flex flex-col p-1 border-red-500/20 bg-black/40">
                        <div className="flex items-center gap-2 p-3 text-red-400 border-b border-red-500/20">
                            <BrainCircuit size={18} />
                            <h3 className="font-mono text-sm uppercase">Case Theory Input</h3>
                        </div>
                        <textarea
                            value={theory}
                            onChange={(e) => setTheory(e.target.value)}
                            placeholder="Pitch your case theory here. Be specific. E.g., 'My client was at the movies during the incident...'"
                            className="flex-1 bg-transparent border-none resize-none p-4 text-sm text-halo-text focus:ring-0 placeholder:text-halo-muted/30 font-mono leading-relaxed custom-scrollbar focus:outline-none"
                        />
                        <div className="p-3 border-t border-red-500/20">
                            <button
                                onClick={handleChallenge}
                                disabled={loading || !theory.trim()}
                                className="w-full py-3 bg-red-600/20 hover:bg-red-600/30 border border-red-500/50 text-red-100 rounded transition-all flex items-center justify-center gap-2 uppercase tracking-widest text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed group"
                            >
                                {loading ? (
                                    <>Processing...</>
                                ) : (
                                    <>
                                        <Gavel size={18} className="group-hover:rotate-12 transition-transform" />
                                        Destroy My Theory
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Results Column */}
                <div className="flex-1 flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
                    {!result && !loading && (
                        <div className="flex-1 flex flex-col items-center justify-center text-red-500/20 gap-4">
                            <ShieldAlert size={64} />
                            <p className="text-lg font-light uppercase tracking-widest">Awaiting Theory...</p>
                        </div>
                    )}

                    {loading && (
                        <div className="flex-1 flex flex-col items-center justify-center text-red-500 animate-pulse gap-4">
                            <Flame size={64} />
                            <p className="text-lg font-light uppercase tracking-widest">Analyzing Weaknesses...</p>
                        </div>
                    )}

                    {result && (
                        <>
                            {/* Assessment */}
                            <div className="bg-red-950/20 border border-red-500/30 rounded-lg p-6 relative overflow-hidden">
                                <div className="absolute top-0 left-0 w-1 h-full bg-red-500" />
                                <h3 className="text-red-400 font-mono text-sm uppercase mb-2 flex items-center gap-2">
                                    <AlertTriangle size={16} />
                                    Ruthless Assessment
                                </h3>
                                <p className="text-red-100 leading-relaxed italic">"{result.overall_assessment}"</p>
                            </div>

                            {/* Weaknesses */}
                            <div className="space-y-3">
                                <h3 className="text-red-400 font-mono text-sm uppercase border-b border-red-500/20 pb-2">Identified Weaknesses</h3>
                                {result.weaknesses.map((w, i) => (
                                    <div key={i} className="bg-black/40 border border-red-500/20 rounded p-4 hover:border-red-500/40 transition-colors">
                                        <h4 className="text-red-200 font-bold text-sm mb-1">{w.point}</h4>
                                        <p className="text-halo-muted text-xs">{w.explanation}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Counter Arguments */}
                            <div className="space-y-3">
                                <h3 className="text-red-400 font-mono text-sm uppercase border-b border-red-500/20 pb-2">Opposing Counsel's Strategy</h3>
                                {result.counter_arguments.map((arg, i) => (
                                    <div key={i} className="bg-black/40 border border-red-500/20 rounded p-4 flex gap-4">
                                        <div className="mt-1">
                                            <ShieldAlert className="text-red-500/50" size={20} />
                                        </div>
                                        <div>
                                            <p className="text-halo-text text-sm mb-2">{arg.argument}</p>
                                            {arg.evidence_cited && (
                                                <div className="text-[10px] text-red-400/60 font-mono bg-red-950/30 px-2 py-1 rounded inline-block">
                                                    Citing: {arg.evidence_cited}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Cross Exam */}
                            <div className="space-y-3">
                                <h3 className="text-red-400 font-mono text-sm uppercase border-b border-red-500/20 pb-2">Cross-Examination Prep</h3>
                                <div className="bg-black/40 border border-red-500/20 rounded p-4">
                                    <ul className="space-y-4">
                                        {result.cross_examination.map((q, i) => (
                                            <li key={i} className="flex gap-3 text-sm text-halo-text">
                                                <span className="text-red-500 font-mono font-bold">Q{i + 1}.</span>
                                                <span>{q}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
