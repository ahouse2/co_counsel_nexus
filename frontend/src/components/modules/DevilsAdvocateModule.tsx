import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, AlertTriangle, Gavel, RefreshCw, CheckCircle } from 'lucide-react';

interface CaseWeakness {
    id: string;
    title: string;
    description: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    suggested_rebuttal: string;
}

interface CrossExamQuestion {
    question: string;
    rationale: string;
    difficulty: string;
}

interface DevilsAdvocateModuleProps {
    caseId: string;
    isActive: boolean;
}

export const DevilsAdvocateModule: React.FC<DevilsAdvocateModuleProps> = ({ caseId, isActive }) => {
    const [weaknesses, setWeaknesses] = useState<CaseWeakness[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'review' | 'crossexam'>('review');

    // Cross Exam State
    const [witnessStatement, setWitnessStatement] = useState("");
    const [crossExamQuestions, setCrossExamQuestions] = useState<CrossExamQuestion[]>([]);
    const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false);

    const fetchReview = async () => {
        setIsLoading(true);
        try {
            const res = await fetch(`/api/devils-advocate/${caseId}/review`);
            if (res.ok) {
                const data = await res.json();
                setWeaknesses(data);
            }
        } catch (error) {
            console.error("Failed to fetch review", error);
        } finally {
            setIsLoading(false);
        }
    };

    const generateCrossExam = async () => {
        if (!witnessStatement.trim()) return;
        setIsGeneratingQuestions(true);
        try {
            const res = await fetch(`/api/devils-advocate/cross-examine`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ witness_statement: witnessStatement })
            });
            if (res.ok) {
                const data = await res.json();
                setCrossExamQuestions(data);
            }
        } catch (error) {
            console.error("Failed to generate cross exam", error);
        } finally {
            setIsGeneratingQuestions(false);
        }
    };

    useEffect(() => {
        if (isActive && activeTab === 'review' && weaknesses.length === 0) {
            fetchReview();
        }
    }, [isActive, caseId]);

    return (
        <div className="h-full w-full flex flex-col bg-slate-950 text-slate-200 p-6 overflow-hidden">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold bg-gradient-to-r from-red-500 to-orange-500 bg-clip-text text-transparent flex items-center gap-2">
                    <ShieldAlert className="w-6 h-6 text-red-500" />
                    Devil's Advocate
                </h2>
            </div>

            <div className="flex gap-4 mb-6">
                <button
                    onClick={() => setActiveTab('review')}
                    className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${activeTab === 'review'
                        ? 'bg-red-500/20 text-red-300 border border-red-500/50'
                        : 'hover:bg-slate-800 text-slate-400'
                        }`}
                >
                    <AlertTriangle className="w-4 h-4" />
                    Case Review
                </button>
                <button
                    onClick={() => setActiveTab('crossexam')}
                    className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${activeTab === 'crossexam'
                        ? 'bg-orange-500/20 text-orange-300 border border-orange-500/50'
                        : 'hover:bg-slate-800 text-slate-400'
                        }`}
                >
                    <Gavel className="w-4 h-4" />
                    Cross-Examination Sim
                </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                <AnimatePresence mode="wait">
                    {activeTab === 'review' ? (
                        <motion.div
                            key="review"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="space-y-4"
                        >
                            {isLoading && weaknesses.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                    <RefreshCw className="w-8 h-8 animate-spin mb-4" />
                                    <p>Analyzing case weaknesses...</p>
                                </div>
                            ) : weaknesses.length === 0 ? (
                                <div className="text-center text-slate-500 py-12">
                                    <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50 text-green-500" />
                                    <p>No major weaknesses detected (or analysis not run).</p>
                                    <button
                                        onClick={fetchReview}
                                        className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm"
                                    >
                                        Run Analysis
                                    </button>
                                </div>
                            ) : (
                                weaknesses.map((item) => (
                                    <div
                                        key={item.id}
                                        className={`p-5 rounded-xl border ${item.severity === 'critical' ? 'bg-red-950/30 border-red-500/50' :
                                            item.severity === 'high' ? 'bg-orange-950/30 border-orange-500/50' :
                                                'bg-slate-900/50 border-slate-700'
                                            }`}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="font-bold text-lg text-slate-100">{item.title}</h3>
                                            <span className={`text-xs px-2 py-1 rounded-full uppercase font-bold ${item.severity === 'critical' ? 'bg-red-500 text-white' :
                                                item.severity === 'high' ? 'bg-orange-500 text-white' :
                                                    'bg-slate-600 text-slate-200'
                                                }`}>
                                                {item.severity}
                                            </span>
                                        </div>
                                        <p className="text-slate-300 mb-4">{item.description}</p>

                                        <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                                            <div className="text-xs font-bold text-green-400 mb-1 uppercase">Suggested Rebuttal</div>
                                            <p className="text-sm text-slate-400">{item.suggested_rebuttal}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    ) : (
                        <motion.div
                            key="crossexam"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="flex flex-col h-full"
                        >
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-400 mb-2">
                                    Witness Statement / Testimony
                                </label>
                                <textarea
                                    value={witnessStatement}
                                    onChange={(e) => setWitnessStatement(e.target.value)}
                                    className="w-full h-32 bg-slate-900 border border-slate-700 rounded-lg p-3 text-slate-200 focus:ring-2 focus:ring-orange-500 focus:outline-none resize-none"
                                    placeholder="Paste the witness statement here..."
                                />
                                <button
                                    onClick={generateCrossExam}
                                    disabled={isGeneratingQuestions || !witnessStatement.trim()}
                                    className="mt-3 px-6 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                                >
                                    {isGeneratingQuestions ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Gavel className="w-4 h-4" />}
                                    Generate Questions
                                </button>
                            </div>

                            <div className="space-y-4">
                                {crossExamQuestions.map((q, idx) => (
                                    <div key={idx} className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl">
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-semibold text-orange-200">Q: {q.question}</h4>
                                            <span className={`text-xs px-2 py-0.5 rounded-full border ${q.difficulty === 'hard' ? 'border-red-500 text-red-400' :
                                                q.difficulty === 'medium' ? 'border-yellow-500 text-yellow-400' :
                                                    'border-green-500 text-green-400'
                                                }`}>
                                                {q.difficulty}
                                            </span>
                                        </div>
                                        <p className="text-sm text-slate-500 italic">Rationale: {q.rationale}</p>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};
