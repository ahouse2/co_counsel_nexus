import { useState, useRef } from 'react';
import { FileText, PenTool, Sparkles, MessageSquare, Save, Download, Wand2, Eraser, Copy, Check } from 'lucide-react';
import { endpoints } from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';

interface DraftTemplate {
    id: string;
    name: string;
    content: string;
    category: string;
}

const TEMPLATES: DraftTemplate[] = [
    {
        id: 'motion-dismiss',
        name: 'Motion to Dismiss',
        category: 'Motions',
        content: `IN THE SUPERIOR COURT OF THE STATE OF CALIFORNIA\nCOUNTY OF LOS ANGELES\n\n[PLAINTIFF NAME],\nPlaintiff,\n\nv.\n\n[DEFENDANT NAME],\nDefendant.\n\nCase No.: [CASE NUMBER]\n\nNOTICE OF MOTION AND MOTION TO DISMISS COMPLAINT; MEMORANDUM OF POINTS AND AUTHORITIES\n\nTO ALL PARTIES AND THEIR ATTORNEYS OF RECORD:\n\nPLEASE TAKE NOTICE that on [DATE] at [TIME], or as soon thereafter as the matter may be heard, in Department [DEPT] of the above-entitled Court, Defendant will, and hereby does, move for an order dismissing the Complaint filed by Plaintiff.\n\nThis motion is made on the grounds that the Complaint fails to state facts sufficient to constitute a cause of action against Defendant.\n\nRespectfully submitted,\n\n______________________\n[ATTORNEY NAME]`
    },
    {
        id: 'demand-letter',
        name: 'Demand Letter',
        category: 'Correspondence',
        content: `[DATE]\n\nVIA CERTIFIED MAIL\n\n[RECIPIENT NAME]\n[ADDRESS]\n\nRe: Demand for Payment - [SUBJECT]\n\nDear [RECIPIENT NAME]:\n\nThis firm represents [CLIENT NAME] in connection with the above-referenced matter. As you are aware, [FACTUAL BASIS FOR CLAIM].\n\nDespite previous attempts to resolve this matter, payment of $[AMOUNT] remains outstanding. This letter serves as a final demand for payment.\n\nUnless we receive payment in full by [DEADLINE DATE], we have been instructed to take all necessary legal action to protect our client's interests, including filing a lawsuit against you.\n\nGOVERN YOURSELF ACCORDINGLY.\n\nSincerely,\n\n[ATTORNEY NAME]`
    }
];

export function DocumentDraftingModule() {
    const [editorContent, setEditorContent] = useState('');
    const [contextQuery, setContextQuery] = useState('');
    const [isAiThinking, setIsAiThinking] = useState(false);
    const [showTemplates, setShowTemplates] = useState(false);
    const [activeTab, setActiveTab] = useState<'chat' | 'refine'>('chat');
    const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
    const [selectedText, setSelectedText] = useState('');
    const editorRef = useRef<HTMLTextAreaElement>(null);

    // Handle text selection for "Refine" feature
    const handleSelect = () => {
        if (editorRef.current) {
            const start = editorRef.current.selectionStart;
            const end = editorRef.current.selectionEnd;
            if (start !== end) {
                setSelectedText(editorContent.substring(start, end));
                setActiveTab('refine');
            } else {
                setSelectedText('');
            }
        }
    };

    const handleMagicInsert = async () => {
        if (!contextQuery.trim()) return;
        setIsAiThinking(true);
        try {
            const response = await endpoints.agents.chat(`Draft a legal clause or paragraph based on this request: ${contextQuery}. Return ONLY the drafted text, no conversational filler.`);
            const text = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

            // Insert at cursor or append
            if (editorRef.current) {
                const start = editorRef.current.selectionStart;
                const end = editorRef.current.selectionEnd;
                const newContent = editorContent.substring(0, start) + text + editorContent.substring(end);
                setEditorContent(newContent);
            } else {
                setEditorContent(prev => prev + '\n\n' + text);
            }
            setContextQuery('');
        } catch (error) {
            console.error("Magic Insert failed:", error);
        } finally {
            setIsAiThinking(false);
        }
    };

    const handleRefine = async (instruction: string) => {
        if (!selectedText) return;
        setIsAiThinking(true);
        try {
            const response = await endpoints.agents.chat(`Rewrite the following text to be ${instruction}. Return ONLY the rewritten text.\n\nTEXT: "${selectedText}"`);
            const text = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

            setAiSuggestions([text]);
        } catch (error) {
            console.error("Refine failed:", error);
        } finally {
            setIsAiThinking(false);
        }
    };

    const applySuggestion = (suggestion: string) => {
        if (editorRef.current && selectedText) {
            const start = editorRef.current.selectionStart;
            const end = editorRef.current.selectionEnd;
            const newContent = editorContent.substring(0, start) + suggestion + editorContent.substring(end);
            setEditorContent(newContent);
            setAiSuggestions([]);
            setSelectedText('');
            setActiveTab('chat');
        }
    };

    const loadTemplate = (template: DraftTemplate) => {
        setEditorContent(template.content);
        setShowTemplates(false);
    };

    return (
        <div className="w-full h-full flex text-halo-text overflow-hidden bg-black/20">
            {/* Left Panel: AI Companion */}
            <div className="w-96 flex flex-col border-r border-halo-border/30 bg-halo-card/20 backdrop-blur-sm">
                <div className="p-4 border-b border-halo-border/30 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-halo-cyan">
                        <Sparkles size={20} />
                        <h3 className="font-mono text-sm uppercase tracking-wider">AI Companion</h3>
                    </div>
                    <div className="flex bg-black/40 rounded p-1">
                        <button
                            onClick={() => setActiveTab('chat')}
                            className={`p-1.5 rounded transition-colors ${activeTab === 'chat' ? 'bg-halo-cyan/20 text-halo-cyan' : 'text-halo-muted hover:text-white'}`}
                            title="Context Chat"
                        >
                            <MessageSquare size={16} />
                        </button>
                        <button
                            onClick={() => setActiveTab('refine')}
                            className={`p-1.5 rounded transition-colors ${activeTab === 'refine' ? 'bg-halo-cyan/20 text-halo-cyan' : 'text-halo-muted hover:text-white'}`}
                            title="Refine Selection"
                        >
                            <Wand2 size={16} />
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                    {activeTab === 'chat' ? (
                        <div className="space-y-4">
                            <div className="bg-halo-cyan/5 border border-halo-cyan/20 rounded-lg p-3 text-sm text-halo-text/80">
                                <p>I can help you draft clauses, find precedents, or format your document. Just describe what you need.</p>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-mono text-halo-muted uppercase">Magic Insert</label>
                                <textarea
                                    value={contextQuery}
                                    onChange={(e) => setContextQuery(e.target.value)}
                                    placeholder="e.g., 'Draft a limitation of liability clause for a SaaS contract'..."
                                    className="w-full h-32 bg-black/40 border border-halo-border rounded-lg p-3 text-sm focus:border-halo-cyan focus:outline-none resize-none"
                                />
                                <button
                                    onClick={handleMagicInsert}
                                    disabled={isAiThinking || !contextQuery.trim()}
                                    className="w-full py-2 bg-halo-cyan/10 hover:bg-halo-cyan/20 border border-halo-cyan/30 text-halo-cyan rounded-lg transition-all flex items-center justify-center gap-2 font-medium text-sm disabled:opacity-50"
                                >
                                    {isAiThinking ? <Sparkles className="animate-spin" size={16} /> : <PenTool size={16} />}
                                    GENERATE & INSERT
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {!selectedText ? (
                                <div className="text-center text-halo-muted py-8">
                                    <Eraser size={32} className="mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">Select text in the editor to refine it.</p>
                                </div>
                            ) : (
                                <>
                                    <div className="bg-black/40 border border-halo-border rounded p-3 text-xs text-halo-muted italic border-l-2 border-l-halo-cyan">
                                        "{selectedText.substring(0, 100)}{selectedText.length > 100 ? '...' : ''}"
                                    </div>

                                    <div className="grid grid-cols-2 gap-2">
                                        <button onClick={() => handleRefine('more formal')} className="p-2 bg-halo-card border border-halo-border hover:border-halo-cyan rounded text-xs transition-colors">More Formal</button>
                                        <button onClick={() => handleRefine('more concise')} className="p-2 bg-halo-card border border-halo-border hover:border-halo-cyan rounded text-xs transition-colors">Concise</button>
                                        <button onClick={() => handleRefine('more aggressive')} className="p-2 bg-halo-card border border-halo-border hover:border-halo-cyan rounded text-xs transition-colors">Aggressive</button>
                                        <button onClick={() => handleRefine('simpler')} className="p-2 bg-halo-card border border-halo-border hover:border-halo-cyan rounded text-xs transition-colors">Simplify</button>
                                    </div>

                                    {isAiThinking && (
                                        <div className="flex justify-center py-4">
                                            <Sparkles className="animate-spin text-halo-cyan" />
                                        </div>
                                    )}

                                    {aiSuggestions.map((suggestion, idx) => (
                                        <motion.div
                                            key={idx}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="bg-halo-cyan/10 border border-halo-cyan/30 rounded-lg p-3 space-y-2"
                                        >
                                            <p className="text-sm text-white">{suggestion}</p>
                                            <button
                                                onClick={() => applySuggestion(suggestion)}
                                                className="w-full py-1.5 bg-halo-cyan text-black rounded text-xs font-bold hover:bg-white transition-colors flex items-center justify-center gap-2"
                                            >
                                                <Check size={14} /> REPLACE SELECTION
                                            </button>
                                        </motion.div>
                                    ))}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Right Panel: Editor */}
            <div className="flex-1 flex flex-col relative">
                {/* Toolbar */}
                <div className="h-14 border-b border-halo-border/30 flex items-center justify-between px-6 bg-halo-bg/50">
                    <div className="flex items-center gap-4">
                        <FileText className="text-halo-muted" size={20} />
                        <input
                            type="text"
                            placeholder="Untitled Document"
                            className="bg-transparent border-none text-halo-text focus:outline-none font-medium placeholder:text-halo-muted/50"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setShowTemplates(!showTemplates)}
                            className="px-3 py-1.5 text-xs font-medium text-halo-text hover:text-halo-cyan transition-colors flex items-center gap-2"
                        >
                            <Copy size={14} /> TEMPLATES
                        </button>
                        <div className="h-4 w-px bg-halo-border/50 mx-2" />
                        <button className="p-2 text-halo-muted hover:text-white transition-colors" title="Save">
                            <Save size={18} />
                        </button>
                        <button className="p-2 text-halo-muted hover:text-white transition-colors" title="Export PDF">
                            <Download size={18} />
                        </button>
                    </div>
                </div>

                {/* Editor Area */}
                <div className="flex-1 overflow-hidden relative bg-[#1a1a1a]">
                    <textarea
                        ref={editorRef}
                        value={editorContent}
                        onChange={(e) => setEditorContent(e.target.value)}
                        onSelect={handleSelect}
                        placeholder="Start typing or use the AI Companion to generate content..."
                        className="w-full h-full p-8 bg-transparent text-gray-300 font-serif text-lg leading-loose resize-none focus:outline-none custom-scrollbar selection:bg-halo-cyan/30 selection:text-white"
                        spellCheck={false}
                    />

                    {/* Template Modal */}
                    <AnimatePresence>
                        {showTemplates && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="absolute top-4 right-4 w-80 bg-halo-card border border-halo-border rounded-xl shadow-2xl z-20 overflow-hidden"
                            >
                                <div className="p-4 border-b border-halo-border/50 bg-black/50">
                                    <h4 className="font-bold text-halo-text text-sm">Document Templates</h4>
                                </div>
                                <div className="max-h-96 overflow-y-auto custom-scrollbar p-2">
                                    {TEMPLATES.map(template => (
                                        <button
                                            key={template.id}
                                            onClick={() => loadTemplate(template)}
                                            className="w-full text-left p-3 rounded hover:bg-halo-cyan/10 hover:border-halo-cyan/30 border border-transparent transition-all group"
                                        >
                                            <div className="font-medium text-halo-text group-hover:text-halo-cyan text-sm">{template.name}</div>
                                            <div className="text-xs text-halo-muted">{template.category}</div>
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
