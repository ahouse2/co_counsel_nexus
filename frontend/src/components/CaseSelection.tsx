import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Case {
  id: string;
}

interface CaseSelectionProps {
  open: boolean;
  onSelect: (caseId: string) => void;
}

export function CaseSelection({ open, onSelect }: CaseSelectionProps) {
  const [cases, setCases] = useState<Case[]>([]);

  useEffect(() => {
    if (open) {
      fetch('/api/cases')
        .then(r => r.json())
        .then(data => setCases(data))
        .catch(console.error);
    }
  }, [open]);

  return (
    <Dialog open={open}>
      <DialogContent className="sm:max-w-[500px] bg-zinc-950 border-zinc-800 text-zinc-100">
        <DialogHeader>
          <DialogTitle>Select Active Matter</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[300px] w-full pr-4">
          <div className="space-y-2">
            {cases.map((c) => (
              <Button
                key={c.id}
                variant="outline"
                className="w-full justify-start text-left border-zinc-700 hover:bg-zinc-900 hover:text-cyan-400"
                onClick={() => onSelect(c.id)}
              >
                <span className="font-mono mr-2">[{c.id}]</span>
                Matter {c.id}
              </Button>
            ))}
            {cases.length === 0 && (
              <div className="text-center text-zinc-500 py-8">
                No active matters found.
                <Button variant="link" onClick={() => onSelect('default-case')}>
                  Initialize Default Case
                </Button>
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
