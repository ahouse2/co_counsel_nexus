import { FileText, PenTool } from 'lucide-react';

export function DocumentDraftingModule() {
    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                    <PenTool className="text-halo-cyan w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Legal Drafting</h2>
                    <p className="text-halo-muted text-sm">Automated document generation and editing</p>
                </div>
            </div>

            <div className="flex-1 flex items-center justify-center border border-dashed border-halo-border/30 rounded-lg bg-black/20">
                <div className="text-center">
                    <FileText className="w-16 h-16 text-halo-muted mx-auto mb-4 opacity-50" />
                    <h3 className="text-xl font-mono text-halo-text mb-2">DRAFTING ENGINE ONLINE</h3>
                    <p className="text-halo-muted max-w-md mx-auto">
                        Select a template or use Context Engine to generate a new legal document based on case facts.
                    </p>
                    <button className="mt-6 px-6 py-2 bg-halo-cyan/20 hover:bg-halo-cyan/30 border border-halo-cyan text-halo-cyan rounded transition-all uppercase tracking-widest text-sm font-bold">
                        New Draft
                    </button>
                </div>
            </div>
        </div>
    );
}
