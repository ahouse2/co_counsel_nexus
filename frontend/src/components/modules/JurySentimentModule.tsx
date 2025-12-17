import { useState } from 'react';
import { endpoints } from '../../services/api';
import { motion } from 'framer-motion';
import { Scale, Users, TrendingUp, AlertTriangle, ThumbsUp, ThumbsDown } from 'lucide-react';

export function JurySentimentModule() {
    const [argumentText, setArgumentText] = useState('');
    const [analysis, setAnalysis] = useState<any>(null);
    const [juryProfile, setJuryProfile] = useState({
        age_range: '35-55',
        education: 'college',
        political_leaning: 'moderate',
    });
    const [simulation, setSimulation] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const analyzeArgument = async () => {
        if (!argumentText.trim()) return;
        setLoading(true);
        setAnalysis(null);
        try {
            const response = await endpoints.jurySentiment.analyzeArgument({ text: argumentText });
            setAnalysis(response.data);
        } catch (error) {
            console.error("Analysis failed:", error);
            alert('Failed to analyze argument. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const simulateJury = async () => {
        if (!argumentText.trim()) return;
        setLoading(true);
        setSimulation(null);
        try {
            const response = await endpoints.jurySentiment.simulateJury({
                argument: argumentText,
                jury_profile: juryProfile,
            });
            setSimulation(response.data);
        } catch (error) {
            console.error("Simulation failed:", error);
            alert('Failed to simulate jury response. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 0.7) return 'text-green-500';
        if (score >= 0.4) return 'text-yellow-500';
        return 'text-red-500';
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                    <Scale className="text-blue-500 w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Jury Sentiment Predictor</h2>
                    <p className="text-halo-muted text-sm">Analyze how arguments resonate with juries</p>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-2 gap-8 overflow-hidden">
                {/* Input Panel */}
                <div className="flex flex-col gap-4">
                    <div className="flex-1 flex flex-col">
                        <label className="text-sm font-mono text-halo-muted uppercase mb-2">Argument Text</label>
                        <textarea
                            value={argumentText}
                            onChange={(e) => setArgumentText(e.target.value)}
                            placeholder="Enter your legal argument here..."
                            className="flex-1 bg-black/50 border border-halo-border rounded-lg p-4 text-sm focus:border-blue-500 focus:outline-none resize-none"
                        />
                    </div>

                    <div className="bg-black/40 border border-halo-border/50 rounded-lg p-4">
                        <h3 className="text-sm font-mono text-halo-muted uppercase mb-4 flex items-center gap-2">
                            <Users size={16} /> Jury Profile
                        </h3>
                        <div className="space-y-3">
                            <div>
                                <label className="text-xs text-halo-muted">Age Range</label>
                                <select
                                    value={juryProfile.age_range}
                                    onChange={(e) => setJuryProfile({ ...juryProfile, age_range: e.target.value })}
                                    className="w-full bg-black/50 border border-halo-border rounded px-3 py-2 text-sm mt-1"
                                    title="Select age range"
                                >
                                    <option value="18-34">18-34</option>
                                    <option value="35-55">35-55</option>
                                    <option value="55+">55+</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-halo-muted">Education</label>
                                <select
                                    value={juryProfile.education}
                                    onChange={(e) => setJuryProfile({ ...juryProfile, education: e.target.value })}
                                    className="w-full bg-black/50 border border-halo-border rounded px-3 py-2 text-sm mt-1"
                                    title="Select education level"
                                >
                                    <option value="high_school">High School</option>
                                    <option value="college">College</option>
                                    <option value="graduate">Graduate</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-halo-muted">Political Leaning</label>
                                <select
                                    value={juryProfile.political_leaning}
                                    onChange={(e) => setJuryProfile({ ...juryProfile, political_leaning: e.target.value })}
                                    className="w-full bg-black/50 border border-halo-border rounded px-3 py-2 text-sm mt-1"
                                    title="Select political leaning"
                                >
                                    <option value="liberal">Liberal</option>
                                    <option value="moderate">Moderate</option>
                                    <option value="conservative">Conservative</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <button
                            onClick={analyzeArgument}
                            disabled={loading || !argumentText.trim()}
                            className="flex-1 px-6 py-3 bg-blue-500/10 hover:bg-blue-500/20 text-blue-500 border border-blue-500/50 rounded-lg transition-all disabled:opacity-50"
                        >
                            Analyze Sentiment
                        </button>
                        <button
                            onClick={simulateJury}
                            disabled={loading || !argumentText.trim()}
                            className="flex-1 px-6 py-3 bg-purple-500/10 hover:bg-purple-500/20 text-purple-500 border border-purple-500/50 rounded-lg transition-all disabled:opacity-50"
                        >
                            Simulate Jury
                        </button>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="overflow-y-auto custom-scrollbar space-y-6">
                    {!loading && !analysis && !simulation && (
                        <div className="flex flex-col items-center justify-center h-full text-halo-muted">
                            <Scale size={64} className="mb-4 opacity-20" />
                            <p className="text-lg mb-2">Ready to Analyze</p>
                            <p className="text-sm text-center">Enter an argument and click a button to begin analysis</p>
                        </div>
                    )}

                    {loading && (
                        <div className="flex items-center justify-center h-full">
                            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                        </div>
                    )}

                    {analysis && !loading && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-black/40 border border-blue-500/30 rounded-xl p-6"
                        >
                            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                                <TrendingUp className="text-blue-500" />
                                Sentiment Analysis
                            </h3>

                            <div className="mb-6">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm text-halo-muted">Overall Persuasiveness</span>
                                    <span className={`text-2xl font-bold ${getScoreColor(analysis.overall_score)}`}>
                                        {(analysis.overall_score * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <div className="h-2 bg-black/50 rounded-full overflow-hidden">
                                    {/* eslint-disable-next-line react/forbid-component-props -- CSS custom properties require style prop */}
                                    <div
                                        className={`h-full transition-all dynamic-width ${analysis.overall_score >= 0.7 ? 'bg-green-500' :
                                            analysis.overall_score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                            }`}
                                        style={{ '--score': `${analysis.overall_score * 100}%` } as React.CSSProperties}
                                    />
                                </div>
                            </div>

                            <div className="mb-4">
                                <span className="text-sm text-halo-muted">Emotional Tone:</span>
                                <span className="ml-2 text-white font-semibold capitalize">{analysis.emotional_tone}</span>
                            </div>

                            <div className="grid gap-4">
                                <div>
                                    <h4 className="text-sm font-mono text-green-400 uppercase mb-2 flex items-center gap-2">
                                        <ThumbsUp size={14} /> Strengths
                                    </h4>
                                    <ul className="space-y-1">
                                        {analysis.strengths.map((strength: string, i: number) => (
                                            <li key={i} className="text-sm text-gray-300 pl-4 border-l-2 border-green-500/30">
                                                {strength}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div>
                                    <h4 className="text-sm font-mono text-red-400 uppercase mb-2 flex items-center gap-2">
                                        <ThumbsDown size={14} /> Weaknesses
                                    </h4>
                                    <ul className="space-y-1">
                                        {analysis.weaknesses.map((weakness: string, i: number) => (
                                            <li key={i} className="text-sm text-gray-300 pl-4 border-l-2 border-red-500/30">
                                                {weakness}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div>
                                    <h4 className="text-sm font-mono text-blue-400 uppercase mb-2 flex items-center gap-2">
                                        <AlertTriangle size={14} /> Recommendations
                                    </h4>
                                    <ul className="space-y-1">
                                        {analysis.recommendations.map((rec: string, i: number) => (
                                            <li key={i} className="text-sm text-gray-300 pl-4 border-l-2 border-blue-500/30">
                                                {rec}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {simulation && !loading && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-black/40 border border-purple-500/30 rounded-xl p-6"
                        >
                            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                                <Users className="text-purple-500" />
                                Jury Simulation
                            </h3>

                            <div className="mb-6">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm text-halo-muted">Receptiveness Score</span>
                                    <span className={`text-2xl font-bold ${getScoreColor(simulation.receptiveness_score)}`}>
                                        {(simulation.receptiveness_score * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <h4 className="text-sm font-mono text-purple-400 uppercase mb-2">Predicted Reactions</h4>
                                    <ul className="space-y-1">
                                        {simulation.predicted_reactions.map((reaction: string, i: number) => (
                                            <li key={i} className="text-sm text-gray-300 pl-4 border-l-2 border-purple-500/30">
                                                {reaction}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                {simulation.concerns.length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-mono text-yellow-400 uppercase mb-2">Concerns</h4>
                                        <ul className="space-y-1">
                                            {simulation.concerns.map((concern: string, i: number) => (
                                                <li key={i} className="text-sm text-gray-300 pl-4 border-l-2 border-yellow-500/30">
                                                    {concern}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>
        </div>
    );
}
