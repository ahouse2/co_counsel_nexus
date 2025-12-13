import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, RefreshCw, AlertTriangle } from 'lucide-react';

interface Contradiction {
  id: string;
  description: string;
  source_a: string;
  source_b: string;
  confidence: number;
  severity: 'high' | 'medium' | 'low';
}

interface NarrativeModuleProps {
  caseId: string;
  isActive: boolean;
}

export const NarrativeModule: React.FC<NarrativeModuleProps> = ({ caseId, isActive }) => {
  const [narrative, setNarrative] = useState<string>("");
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'narrative' | 'contradictions'>('narrative');

  const fetchNarrative = async () => {
    setIsLoading(true);
    try {
      // Use direct fetch or api service if available. 
      // Assuming proxy is set up to forward /api to backend
      const res = await fetch(`/api/narrative/${caseId}/generate`);
      if (res.ok) {
        const data = await res.json();
        setNarrative(data.narrative);
      }
    } catch (error) {
      console.error("Failed to fetch narrative", error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchContradictions = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/narrative/${caseId}/contradictions`);
      if (res.ok) {
        const data = await res.json();
        setContradictions(data);
      }
    } catch (error) {
      console.error("Failed to fetch contradictions", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isActive) {
      if (!narrative) fetchNarrative();
      if (contradictions.length === 0) fetchContradictions();
    }
  }, [isActive, caseId]);

  return (
    <div className="h-full w-full flex flex-col bg-slate-950 text-slate-200 p-6 overflow-hidden">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-purple-400" />
          Narrative Weaver
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => activeTab === 'narrative' ? fetchNarrative() : fetchContradictions()}
            className="p-2 hover:bg-slate-800 rounded-full transition-colors"
            title="Regenerate"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setActiveTab('narrative')}
          className={`px-4 py-2 rounded-lg transition-all ${activeTab === 'narrative'
            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
            : 'hover:bg-slate-800 text-slate-400'
            }`}
        >
          Case Narrative
        </button>
        <button
          onClick={() => setActiveTab('contradictions')}
          className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${activeTab === 'contradictions'
            ? 'bg-red-500/20 text-red-300 border border-red-500/50'
            : 'hover:bg-slate-800 text-slate-400'
            }`}
        >
          Contradictions
          {contradictions.length > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
              {contradictions.length}
            </span>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <AnimatePresence mode="wait">
          {activeTab === 'narrative' ? (
            <motion.div
              key="narrative"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="prose prose-invert max-w-none"
            >
              {isLoading && !narrative ? (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                  <RefreshCw className="w-8 h-8 animate-spin mb-4" />
                  <p>Weaving narrative from evidence...</p>
                </div>
              ) : (
                <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-800 leading-relaxed whitespace-pre-wrap">
                  {narrative || "No narrative generated yet."}
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="contradictions"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              {isLoading && contradictions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                  <RefreshCw className="w-8 h-8 animate-spin mb-4" />
                  <p>Analyzing contradictions...</p>
                </div>
              ) : contradictions.length === 0 ? (
                <div className="text-center text-slate-500 py-12">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No contradictions detected.</p>
                </div>
              ) : (
                contradictions.map((item) => (
                  <div
                    key={item.id}
                    className={`p-4 rounded-xl border ${item.severity === 'high' ? 'bg-red-950/20 border-red-500/30' :
                      item.severity === 'medium' ? 'bg-orange-950/20 border-orange-500/30' :
                        'bg-yellow-950/20 border-yellow-500/30'
                      }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-slate-200">{item.description}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full uppercase font-bold ${item.severity === 'high' ? 'bg-red-500/20 text-red-400' :
                        item.severity === 'medium' ? 'bg-orange-500/20 text-orange-400' :
                          'bg-yellow-500/20 text-yellow-400'
                        }`}>
                        {item.severity}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-sm">
                      <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/50">
                        <div className="flex items-center gap-2 text-slate-400 mb-1">
                          <div className="w-2 h-2 rounded-full bg-blue-400" />
                          Source A
                        </div>
                        <p className="text-slate-300">{item.source_a}</p>
                      </div>
                      <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/50">
                        <div className="flex items-center gap-2 text-slate-400 mb-1">
                          <div className="w-2 h-2 rounded-full bg-purple-400" />
                          Source B
                        </div>
                        <p className="text-slate-300">{item.source_b}</p>
                      </div>
                    </div>

                    <div className="mt-3 flex justify-end">
                      <span className="text-xs text-slate-500">
                        Confidence: {(item.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};