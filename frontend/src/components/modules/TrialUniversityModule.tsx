import { useState, useEffect, useRef } from 'react';
import { GraduationCap, PlayCircle, BookOpen, Loader2, ArrowRight } from 'lucide-react';
import { endpoints } from '../../services/api';

interface Topic {
    id: string;
    title: string;
    description: string;
    prompt: string;
}

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export function TrialUniversityModule() {
    const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [caseContext, setCaseContext] = useState<string>('');

    const topics: Topic[] = [
        {
            id: 'cross-exam',
            title: 'Cross-Examination',
            description: 'Master the art of controlling the witness.',
            prompt: 'You are an expert legal instructor specializing in Cross-Examination. Explain the "Three Rules of Cross-Examination" (leading questions only, one new fact per question, break the witness) and then ask me a practice scenario question based on the current case facts.'
        },
        {
            id: 'evidence',
            title: 'Rules of Evidence',
            description: 'Hearsay exceptions and admissibility.',
            prompt: 'You are an expert legal instructor specializing in the Federal Rules of Evidence. Give me a brief overview of the "Hearsay Rule" and its three most common exceptions, then quiz me with a hypothetical scenario based on the current case.'
        },
        {
            id: 'opening',
            title: 'Opening Statements',
            description: 'Crafting a compelling narrative.',
            prompt: 'You are an expert legal instructor specializing in Opening Statements. Explain the concept of "Primacy and Recency" in the context of a jury trial, and how to use it to frame this specific case.'
        },
        {
            id: 'jury',
            title: 'Jury Selection',
            description: 'Voir dire strategies and psychology.',
            prompt: 'You are an expert legal instructor specializing in Jury Selection (Voir Dire). Explain the difference between a challenge for cause and a peremptory challenge, and strategic considerations for this case.'
        }
    ];

    useEffect(() => {
        // Fetch case context on mount
        const fetchContext = async () => {
            try {
                const res = await endpoints.context.query("Summarize the key facts and legal issues of this case for a law student.");
                setCaseContext(res.data?.response || "No specific case context available.");
            } catch (e) {
                console.error("Failed to fetch context", e);
                setCaseContext("Standard legal training context.");
            }
        };
        fetchContext();
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleStartTopic = async (topic: Topic) => {
        setActiveTopic(topic);
        setMessages([]);
        setLoading(true);

        try {
            const fullPrompt = `${topic.prompt}\n\nCASE CONTEXT:\n${caseContext}`;
            const response = await endpoints.agents.chat(fullPrompt);
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

            setMessages([
                { id: 'sys-1', role: 'assistant', content: answer }
            ]);
        } catch (error) {
            console.error("Failed to start lesson:", error);
            setMessages([
                { id: 'err-1', role: 'assistant', content: "I apologize, but I'm having trouble connecting to the knowledge base right now. Please try again." }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg: Message = { id: `u-${Date.now()}`, role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            // In a real app, we'd send the whole history. For now, we append context to the latest message if it's a new turn, 
            // or rely on the backend session if it exists. We'll just send the input for now, assuming the agent has "memory" or we just do single turn.
            // To improve, we could send `messages` history.
            const response = await endpoints.agents.chat(input);
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

            const botMsg: Message = { id: `a-${Date.now()}`, role: 'assistant', content: answer };
            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            console.error("Failed to send message:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex-1 flex h-full p-6 gap-6 overflow-hidden">
            {/* Topics List */}
            <div className="w-1/3 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-2">
                <div className="mb-4">
                    <h2 className="text-2xl font-light text-halo-text mb-2">Trial University</h2>
                    <p className="text-halo-muted text-sm">Select a module to begin your personalized AI tutoring session.</p>
                </div>

                {topics.map((topic) => (
                    <div
                        key={topic.id}
                        onClick={() => handleStartTopic(topic)}
                        className={`p-4 rounded border cursor-pointer group transition-all relative overflow-hidden
                            ${activeTopic?.id === topic.id
                                ? 'bg-halo-cyan/10 border-halo-cyan shadow-[0_0_15px_rgba(0,240,255,0.2)]'
                                : 'bg-halo-card/50 border-halo-border hover:border-halo-cyan/50'
                            }`}
                    >
                        <div className="flex justify-between items-start mb-2 relative z-10">
                            <div className={`p-2 rounded transition-colors ${activeTopic?.id === topic.id ? 'bg-halo-cyan text-black' : 'bg-halo-bg text-halo-cyan'}`}>
                                <GraduationCap size={20} />
                            </div>
                            {activeTopic?.id === topic.id && <PlayCircle className="text-halo-cyan animate-pulse" size={20} />}
                        </div>
                        <h3 className="font-medium text-halo-text mb-1 relative z-10">{topic.title}</h3>
                        <p className="text-xs text-halo-muted relative z-10">{topic.description}</p>

                        {/* Hover Effect */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-halo-cyan/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />
                    </div>
                ))}
            </div>

            {/* Chat Interface */}
            <div className="flex-1 bg-halo-card border border-halo-border rounded-lg flex flex-col overflow-hidden relative">
                {activeTopic ? (
                    <>
                        {/* Chat Header */}
                        <div className="p-4 border-b border-halo-border bg-halo-bg/50 flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <BookOpen className="text-halo-cyan" size={20} />
                                <span className="font-mono text-sm uppercase tracking-wider text-halo-text">{activeTopic.title}</span>
                            </div>
                            <div className="text-xs text-halo-muted flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                TUTOR ONLINE
                            </div>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar" ref={scrollRef}>
                            {messages.map((msg) => (
                                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[80%] p-4 rounded-lg text-sm leading-relaxed ${msg.role === 'user'
                                        ? 'bg-halo-cyan/10 border border-halo-cyan/30 text-halo-text rounded-tr-none'
                                        : 'bg-halo-bg border border-halo-border text-halo-muted rounded-tl-none'
                                        }`}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="bg-halo-bg border border-halo-border p-4 rounded-lg rounded-tl-none flex items-center gap-2 text-halo-cyan">
                                        <Loader2 size={16} className="animate-spin" />
                                        <span className="text-xs font-mono">THINKING...</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input */}
                        <div className="p-4 border-t border-halo-border bg-halo-bg/50">
                            <form onSubmit={handleSendMessage} className="relative">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Ask a question or respond to the quiz..."
                                    className="w-full bg-black/50 border border-halo-border rounded-lg pl-4 pr-12 py-3 text-sm focus:border-halo-cyan focus:outline-none transition-colors"
                                    disabled={loading}
                                />
                                <button
                                    type="submit"
                                    disabled={!input.trim() || loading}
                                    className="absolute right-2 top-2 p-1.5 bg-halo-cyan text-black rounded hover:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <ArrowRight size={16} />
                                </button>
                            </form>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-halo-muted p-8 text-center">
                        <div className="w-20 h-20 rounded-full bg-halo-bg border border-halo-border flex items-center justify-center mb-6">
                            <GraduationCap size={40} className="opacity-50" />
                        </div>
                        <h3 className="text-xl font-light text-halo-text mb-2">Welcome to Trial University</h3>
                        <p className="max-w-md">Select a module from the left to begin your interactive session with an expert AI legal tutor.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
