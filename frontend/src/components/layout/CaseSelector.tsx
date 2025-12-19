/**
 * CaseSelector - Dropdown for selecting/creating cases
 * 
 * Features:
 * - Lists all existing cases from API
 * - Creates new cases
 * - Persists selection to localStorage via HaloContext
 */

import { useState } from 'react';
import { useHalo } from '../../context/HaloContext';
import { Briefcase, Plus, ChevronDown } from 'lucide-react';

export function CaseSelector() {
    const { caseId, setCaseId, cases, createCase, refreshCases } = useHalo();
    const [isOpen, setIsOpen] = useState(false);
    const [isCreating, setIsCreating] = useState(false);
    const [newCaseName, setNewCaseName] = useState('');

    const currentCase = cases.find(c => c.id === caseId);
    const displayName = currentCase?.name || caseId || 'Select Case';

    const handleCreateCase = async () => {
        if (!newCaseName.trim()) return;

        setIsCreating(true);
        await createCase(newCaseName.trim());
        setNewCaseName('');
        setIsCreating(false);
        setIsOpen(false);
    };

    return (
        <div className="relative">
            {/* Trigger Button */}
            <button
                onClick={() => { setIsOpen(!isOpen); refreshCases(); }}
                className="w-full flex items-center justify-between gap-2 p-3 rounded-lg bg-halo-cyan/10 border border-halo-cyan/30 hover:border-halo-cyan/50 transition-all"
                title="Select Case"
            >
                <div className="flex items-center gap-2 min-w-0">
                    <Briefcase size={16} className="text-halo-cyan flex-shrink-0" />
                    <span className="text-sm text-halo-text truncate">{displayName}</span>
                </div>
                <ChevronDown size={14} className={`text-halo-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-halo-border rounded-lg shadow-xl z-50 max-h-64 overflow-auto">
                    {/* New Case Input */}
                    <div className="p-2 border-b border-halo-border">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={newCaseName}
                                onChange={(e) => setNewCaseName(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleCreateCase()}
                                placeholder="New case name..."
                                className="flex-1 px-2 py-1 text-sm bg-gray-800 border border-gray-700 rounded text-white"
                            />
                            <button
                                onClick={handleCreateCase}
                                disabled={!newCaseName.trim() || isCreating}
                                className="px-2 py-1 bg-halo-cyan text-black rounded text-sm font-medium disabled:opacity-50"
                                title="Create new case"
                            >
                                <Plus size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Case List */}
                    {cases.length === 0 ? (
                        <div className="p-3 text-sm text-halo-muted text-center">
                            No cases yet. Create one above.
                        </div>
                    ) : (
                        cases.map((c) => (
                            <button
                                key={c.id}
                                onClick={() => { setCaseId(c.id); setIsOpen(false); }}
                                className={`w-full flex items-center gap-2 p-3 text-left text-sm hover:bg-gray-800 transition-colors ${c.id === caseId ? 'bg-halo-cyan/10 text-halo-cyan' : 'text-halo-text'
                                    }`}
                            >
                                <Briefcase size={14} className="flex-shrink-0" />
                                <div className="min-w-0">
                                    <div className="font-medium truncate">{c.name}</div>
                                    {c.description && (
                                        <div className="text-xs text-halo-muted truncate">{c.description}</div>
                                    )}
                                </div>
                            </button>
                        ))
                    )}
                </div>
            )}

            {/* Click outside to close */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </div>
    );
}
