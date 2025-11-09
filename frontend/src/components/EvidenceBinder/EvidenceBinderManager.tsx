import React, { useState, useEffect } from 'react';
import { PlusCircle, Trash2, Edit, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface EvidenceItem {
  document_id: string;
  name: string;
  description?: string;
  added_at: string;
}

interface EvidenceBinder {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  items: EvidenceItem[];
}

const EvidenceBinderManager: React.FC = () => {
  const [binders, setBinders] = useState<EvidenceBinder[]>([]);
  const [newBinderName, setNewBinderName] = useState('');
  const [newBinderDescription, setNewBinderDescription] = useState('');
  const [editingBinder, setEditingBinder] = useState<EvidenceBinder | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // Placeholder for API calls
  const fetchBinders = async () => {
    // In a real app, fetch from backend
    setBinders([
      { id: "1", name: "Divorce Case 2025", description: "All evidence for the divorce case.", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), items: [] },
      { id: "2", name: "Client X - Contract Dispute", description: "Documents related to contract dispute.", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), items: [] },
    ]);
  };

  useEffect(() => {
    fetchBinders();
  }, []);

  const handleCreateBinder = async () => {
    if (!newBinderName.trim()) return;
    // In a real app, send to backend
    const newBinder: EvidenceBinder = {
      id: String(binders.length + 1),
      name: newBinderName,
      description: newBinderDescription,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      items: [],
    };
    setBinders([...binders, newBinder]);
    setNewBinderName('');
    setNewBinderDescription('');
    setIsCreateDialogOpen(false);
  };

  const handleDeleteBinder = async (id: string) => {
    // In a real app, send delete request to backend
    setBinders(binders.filter(binder => binder.id !== id));
  };

  const handleEditBinder = (binder: EvidenceBinder) => {
    setEditingBinder(binder);
    setNewBinderName(binder.name);
    setNewBinderDescription(binder.description || '');
    setIsCreateDialogOpen(true);
  };

  const handleUpdateBinder = async () => {
    if (!editingBinder || !newBinderName.trim()) return;
    // In a real app, send update request to backend
    setBinders(binders.map(binder =>
      binder.id === editingBinder.id
        ? { ...binder, name: newBinderName, description: newBinderDescription, updated_at: new Date().toISOString() }
        : binder
    ));
    setEditingBinder(null);
    setNewBinderName('');
    setNewBinderDescription('');
    setIsCreateDialogOpen(false);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-100">Evidence Binders</h2>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => { setEditingBinder(null); setNewBinderName(''); setNewBinderDescription(''); setIsCreateDialogOpen(true); }}>
              <PlusCircle className="mr-2 h-4 w-4" /> Create New Binder
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px] bg-gray-900 text-gray-100 border-gray-700">
            <DialogHeader>
              <DialogTitle>{editingBinder ? 'Edit Binder' : 'Create New Binder'}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right text-gray-300">Name</Label>
                <Input
                  id="name"
                  value={newBinderName}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewBinderName(e.target.value)}
                  className="col-span-3 bg-gray-800 border-gray-700 text-gray-100"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="description" className="text-right text-gray-300">Description</Label>
                <Textarea
                  id="description"
                  value={newBinderDescription}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewBinderDescription(e.target.value)}
                  className="col-span-3 bg-gray-800 border-gray-700 text-gray-100"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" onClick={editingBinder ? handleUpdateBinder : handleCreateBinder}>
                {editingBinder ? 'Save Changes' : 'Create Binder'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {binders.map((binder) => (
          <div key={binder.id} className="bg-gray-800 rounded-lg shadow-lg p-5 border border-gray-700 flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-semibold text-gray-100 flex items-center">
                <FolderOpen className="mr-2 h-5 w-5 text-blue-400" /> {binder.name}
              </h3>
              <p className="text-gray-400 text-sm mt-2">{binder.description || 'No description provided.'}</p>
              <p className="text-gray-500 text-xs mt-3">Created: {new Date(binder.created_at).toLocaleDateString()}</p>
              <p className="text-gray-500 text-xs">Last Updated: {new Date(binder.updated_at).toLocaleDateString()}</p>
            </div>
            <div className="flex space-x-2 mt-4">
              <Button variant="outline" size="sm" onClick={() => handleEditBinder(binder)} className="text-blue-400 border-blue-400 hover:bg-blue-900">
                <Edit className="h-4 w-4" />
              </Button>
              <Button variant="destructive" size="sm" onClick={() => handleDeleteBinder(binder.id)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EvidenceBinderManager;
