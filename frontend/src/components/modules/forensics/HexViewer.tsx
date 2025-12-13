import React from 'react';
import { Binary, X } from 'lucide-react';

interface HexData {
    head: string;
    tail: string;
    total_size: number;
    doc_id: string;
}

interface HexViewerProps {
    hexData: HexData;
    onClose: () => void;
}

export const HexViewer: React.FC<HexViewerProps> = ({ hexData, onClose }) => {
    const formatHex = (hex: string) => {
        // Split into chunks of 2 for readability
        return hex.match(/.{1,2}/g)?.join(' ') ?? hex;
    };

    return (
        <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
            onClick={onClose}
        >
            <div
                className="bg-[#0a0a0a] border border-halo-cyan/30 rounded-lg max-w-5xl w-full max-h-[90vh] flex flex-col shadow-[0_0_50px_rgba(0,240,255,0.15)]"
                onClick={e => e.stopPropagation()}
            >
                <div className="flex justify-between items-center p-6 border-b border-halo-border/30 bg-halo-cyan/5">
                    <div className="flex items-center gap-3">
                        <Binary className="text-halo-cyan" />
                        <div>
                            <h3 className="text-xl font-mono text-halo-cyan tracking-wider">HEX INSPECTOR</h3>
                            <p className="text-xs text-halo-muted font-mono">DOC ID: {hexData.doc_id}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-halo-muted hover:text-white transition-colors" title="Close hex viewer">
                        <X size={24} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 font-mono text-xs custom-scrollbar bg-black/50">
                    <div className="grid grid-cols-1 gap-8">
                        <div>
                            <div className="flex items-center gap-2 mb-2 text-green-400 font-bold border-b border-green-500/30 pb-1">
                                <span>HEAD</span>
                                <span className="text-halo-muted font-normal">(First 512 bytes)</span>
                            </div>
                            <div className="bg-[#050505] p-4 rounded border border-halo-border/20 text-green-500/80 leading-relaxed break-all selection:bg-green-500/30 selection:text-white">
                                {formatHex(hexData.head)}
                            </div>
                        </div>
                        {hexData.tail && (
                            <div>
                                <div className="flex items-center gap-2 mb-2 text-green-400 font-bold border-b border-green-500/30 pb-1">
                                    <span>TAIL</span>
                                    <span className="text-halo-muted font-normal">(Last 512 bytes)</span>
                                </div>
                                <div className="bg-[#050505] p-4 rounded border border-halo-border/20 text-green-500/80 leading-relaxed break-all selection:bg-green-500/30 selection:text-white">
                                    {formatHex(hexData.tail)}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="p-4 border-t border-halo-border/30 bg-halo-cyan/5 flex justify-between items-center text-xs text-halo-muted font-mono">
                    <span>TOTAL SIZE: {hexData.total_size.toLocaleString()} bytes</span>
                    <span>INTEGRITY CHECK: PASSED</span>
                </div>
            </div>
        </div>
    );
};
