import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';

interface Message {
    id: number;
    role: 'system' | 'user';
    content: string;
    isTyping?: boolean;
}

export function ChatModule() {
    const { caseId } = useHalo();
    const [messages, setMessages] = useState<Message[]>([
        { id: 1, role: 'system', content: 'Neuro-SAN Agent System Online. How can I assist with the discovery process?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg: Message = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            // Call API with caseId for context
            const response = await endpoints.agents.chat(userMsg.content, caseId);
            const botResponse = response.data.response || "I processed your request but received no specific output.";

            // Add bot message with typing effect placeholder
            const botMsgId = Date.now() + 1;
            setMessages(prev => [...prev, { id: botMsgId, role: 'system', content: '', isTyping: true }]);

            // Simulate typewriter effect
            let i = 0;
            const typeInterval = setInterval(() => {
                setMessages(prev => prev.map(msg => {
                    if (msg.id === botMsgId) {
                        return { ...msg, content: botResponse.substring(0, i + 1) };
                    }
                    return msg;
                }));
                i++;
                if (i === botResponse.length) {
                    clearInterval(typeInterval);
                    setMessages(prev => prev.map(msg => {
                        if (msg.id === botMsgId) {
                            return { ...msg, isTyping: false };
                        }
                        return msg;
                    }));
                }
            }, 20); // Speed of typing

        } catch (error) {
            console.error("Chat API Error:", error);
            setMessages(prev => [...prev, { id: Date.now() + 1, role: 'system', content: 'Error: Unable to reach the Neural Core. Please try again.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col h-full p-6 max-w-4xl mx-auto w-full">
            <div className="flex-1 overflow-y-auto space-y-4 mb-6 pr-2 custom-scrollbar">
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'system' ? 'bg-halo-cyan/20 text-halo-cyan shadow-[0_0_10px_rgba(0,240,255,0.3)]' : 'bg-halo-card border border-halo-border text-halo-text'}`}>
                            {msg.role === 'system' ? <Bot size={16} /> : <User size={16} />}
                        </div>
                        <div className={`p-4 rounded-lg max-w-[80%] ${msg.role === 'system' ? 'bg-halo-card border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.1)]' : 'bg-halo-cyan/10 border border-halo-cyan/30'}`}>
                            <p className="text-sm leading-relaxed font-mono whitespace-pre-wrap">
                                {msg.content}
                                {msg.isTyping && <span className="animate-pulse inline-block w-2 h-4 bg-halo-cyan ml-1 align-middle"></span>}
                            </p>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="relative">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder={isLoading ? "Neural Core processing..." : "Ask the Co-Counsel..."}
                    disabled={isLoading}
                    className="w-full bg-halo-card border border-halo-border rounded-lg pl-4 pr-12 py-4 focus:border-halo-cyan focus:shadow-[0_0_10px_rgba(0,240,255,0.2)] focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed font-mono text-sm"
                />
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="absolute right-2 top-2 p-2 text-halo-cyan hover:bg-halo-cyan/10 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                </button>
            </div>
        </div>
    );
}
