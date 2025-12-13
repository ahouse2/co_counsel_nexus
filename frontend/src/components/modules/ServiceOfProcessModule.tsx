import { useState } from 'react';
import { Send, MapPin, Check, Clock, AlertCircle, FileText, Plus, Trash2, Eye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ServiceRecord {
    id: string;
    documentName: string;
    recipientName: string;
    recipientAddress: string;
    status: 'pending' | 'in_transit' | 'served' | 'failed';
    servedDate?: string;
    servedBy?: string;
    notes?: string;
    createdAt: string;
}

const mockRecords: ServiceRecord[] = [
    {
        id: '1',
        documentName: 'Summons and Complaint',
        recipientName: 'John Defendant',
        recipientAddress: '123 Main St, Los Angeles, CA 90001',
        status: 'served',
        servedDate: '2024-01-15',
        servedBy: 'ABC Process Server',
        createdAt: '2024-01-10'
    },
    {
        id: '2',
        documentName: 'Motion for Summary Judgment',
        recipientName: 'Jane Corporate',
        recipientAddress: '456 Business Ave, Suite 100, LA 90210',
        status: 'in_transit',
        createdAt: '2024-02-01'
    },
    {
        id: '3',
        documentName: 'Subpoena Duces Tecum',
        recipientName: 'Records Custodian',
        recipientAddress: '789 Hospital Way, LA 90012',
        status: 'pending',
        createdAt: '2024-02-10'
    },
];

const statusConfig = {
    pending: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', label: 'Pending', icon: Clock },
    in_transit: { color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30', label: 'In Transit', icon: Send },
    served: { color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30', label: 'Served', icon: Check },
    failed: { color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30', label: 'Failed', icon: AlertCircle },
};

export function ServiceOfProcessModule() {
    const [records, setRecords] = useState<ServiceRecord[]>(mockRecords);
    const [selectedRecord, setSelectedRecord] = useState<ServiceRecord | null>(null);
    // const [showAddModal, setShowAddModal] = useState(false);
    // const [loading, setLoading] = useState(false);

    const getStatusInfo = (status: ServiceRecord['status']) => statusConfig[status];

    const handleDelete = (id: string) => {
        setRecords(prev => prev.filter(r => r.id !== id));
        if (selectedRecord?.id === id) setSelectedRecord(null);
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Send className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Service of Process</h2>
                        <p className="text-halo-muted text-sm">Track and verify legal service delivery</p>
                    </div>
                </div>
                <button
                    onClick={() => console.log("Add modal not implemented")}
                    className="flex items-center gap-2 px-4 py-2 bg-halo-cyan/20 hover:bg-halo-cyan/30 text-halo-cyan border border-halo-cyan/30 rounded-lg transition-all"
                >
                    <Plus size={18} />
                    <span className="text-sm uppercase tracking-wider">New Service Request</span>
                </button>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-4 gap-4 mb-6 shrink-0">
                {Object.entries(statusConfig).map(([key, config]) => {
                    const count = records.filter(r => r.status === key).length;
                    const Icon = config.icon;
                    return (
                        <motion.div
                            key={key}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`p-4 rounded-lg border ${config.border} ${config.bg} backdrop-blur-sm`}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-2xl font-bold">{count}</p>
                                    <p className={`text-xs uppercase tracking-wider ${config.color}`}>{config.label}</p>
                                </div>
                                <Icon className={`${config.color} w-6 h-6 opacity-60`} />
                            </div>
                        </motion.div>
                    );
                })}
            </div>

            {/* Main Content */}
            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Records List */}
                <div className="flex-1 flex flex-col bg-black/30 rounded-lg border border-halo-border overflow-hidden">
                    <div className="p-4 border-b border-halo-border/50 flex items-center gap-2 text-halo-muted">
                        <FileText size={16} />
                        <span className="text-xs uppercase tracking-wider font-mono">Service Records</span>
                        <span className="ml-auto text-xs">{records.length} total</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                        <AnimatePresence>
                            {records.map((record, idx) => {
                                const statusInfo = getStatusInfo(record.status);
                                return (
                                    <motion.div
                                        key={record.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: 20 }}
                                        transition={{ delay: idx * 0.05 }}
                                        onClick={() => setSelectedRecord(record)}
                                        className={`p-4 rounded-lg border cursor-pointer transition-all ${selectedRecord?.id === record.id
                                            ? 'border-halo-cyan bg-halo-cyan/10'
                                            : 'border-halo-border/50 bg-black/20 hover:border-halo-cyan/50'
                                            }`}
                                    >
                                        <div className="flex items-start justify-between mb-2">
                                            <h4 className="font-medium text-halo-text">{record.documentName}</h4>
                                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${statusInfo.bg} ${statusInfo.color} ${statusInfo.border} border`}>
                                                {statusInfo.label.toUpperCase()}
                                            </span>
                                        </div>
                                        <p className="text-sm text-halo-muted flex items-center gap-1">
                                            <MapPin size={12} />
                                            {record.recipientName}
                                        </p>
                                        <p className="text-xs text-halo-muted/60 mt-1">{record.recipientAddress}</p>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Detail Panel */}
                <div className="w-96 bg-black/30 rounded-lg border border-halo-border overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-halo-border/50 flex items-center gap-2 text-halo-muted">
                        <Eye size={16} />
                        <span className="text-xs uppercase tracking-wider font-mono">Details</span>
                    </div>
                    <div className="flex-1 p-4 overflow-y-auto custom-scrollbar">
                        {selectedRecord ? (
                            <motion.div
                                key={selectedRecord.id}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-4"
                            >
                                <div>
                                    <label className="text-xs text-halo-muted uppercase tracking-wider">Document</label>
                                    <p className="text-lg font-medium text-halo-text">{selectedRecord.documentName}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-halo-muted uppercase tracking-wider">Recipient</label>
                                    <p className="text-halo-text">{selectedRecord.recipientName}</p>
                                    <p className="text-sm text-halo-muted">{selectedRecord.recipientAddress}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-halo-muted uppercase tracking-wider">Status</label>
                                    <div className={`inline-flex items-center gap-2 px-3 py-1 mt-1 rounded ${getStatusInfo(selectedRecord.status).bg} ${getStatusInfo(selectedRecord.status).border} border`}>
                                        {(() => { const Icon = getStatusInfo(selectedRecord.status).icon; return <Icon size={14} className={getStatusInfo(selectedRecord.status).color} />; })()}
                                        <span className={`text-sm font-medium ${getStatusInfo(selectedRecord.status).color}`}>
                                            {getStatusInfo(selectedRecord.status).label}
                                        </span>
                                    </div>
                                </div>
                                {selectedRecord.servedDate && (
                                    <div>
                                        <label className="text-xs text-halo-muted uppercase tracking-wider">Served On</label>
                                        <p className="text-halo-cyan">{new Date(selectedRecord.servedDate).toLocaleDateString()}</p>
                                    </div>
                                )}
                                {selectedRecord.servedBy && (
                                    <div>
                                        <label className="text-xs text-halo-muted uppercase tracking-wider">Served By</label>
                                        <p className="text-halo-text">{selectedRecord.servedBy}</p>
                                    </div>
                                )}
                                <div className="pt-4 border-t border-halo-border/30">
                                    <button
                                        onClick={() => handleDelete(selectedRecord.id)}
                                        className="flex items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 rounded transition-colors text-sm"
                                    >
                                        <Trash2 size={14} />
                                        Delete Record
                                    </button>
                                </div>
                            </motion.div>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-halo-muted/50">
                                <MapPin size={40} className="mb-3" />
                                <p className="text-sm text-center">Select a service record to view details</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
