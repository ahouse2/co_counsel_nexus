
import { Settings, Menu } from 'lucide-react';

export function TopBar() {
    return (
        <header className="h-16 border-b border-halo-border bg-halo-bg flex items-center justify-between px-6 z-20 relative">
            <div className="flex items-center gap-4">
                <button className="p-2 text-halo-muted hover:text-halo-text transition-colors border border-halo-border rounded hover:border-halo-text">
                    <Menu className="w-4 h-4" />
                    <span className="sr-only">Menu</span>
                </button>
            </div>

            <h1 className="text-halo-text font-medium tracking-[0.2em] text-sm uppercase">
                AI-Driven Legal Discovery
            </h1>

            <div className="flex items-center gap-4">
                <button className="p-2 text-halo-muted hover:text-halo-text transition-colors border border-halo-border rounded-full hover:border-halo-text hover:bg-halo-card">
                    <Settings className="w-4 h-4" />
                    <span className="sr-only">Settings</span>
                </button>
            </div>
        </header>
    );
}
