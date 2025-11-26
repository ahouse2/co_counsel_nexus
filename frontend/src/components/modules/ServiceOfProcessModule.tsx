import { Send, MapPin } from 'lucide-react';

export function ServiceOfProcessModule() {
    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                    <Send className="text-halo-cyan w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Service of Process</h2>
                    <p className="text-halo-muted text-sm">Tracking and verification of legal service</p>
                </div>
            </div>

            <div className="flex-1 flex items-center justify-center border border-dashed border-halo-border/30 rounded-lg bg-black/20">
                <div className="text-center">
                    <MapPin className="w-16 h-16 text-halo-muted mx-auto mb-4 opacity-50" />
                    <h3 className="text-xl font-mono text-halo-text mb-2">SERVICE TRACKER</h3>
                    <p className="text-halo-muted max-w-md mx-auto">
                        Monitor status of served documents. Integration with process server API required for live updates.
                    </p>
                </div>
            </div>
        </div>
    );
}
