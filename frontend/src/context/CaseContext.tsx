import React, { createContext, useContext, useEffect, useState } from 'react';

export type CaseContextValue = {
  caseId: string | null;
  setCaseId: (id: string) => void;
  memory: any;
  refreshMemory: () => void;
  isLoading: boolean;
};

export const CaseContext = createContext<CaseContextValue | undefined>(undefined);

export const CaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [caseId, setCaseId] = useState<string | null>(null);
  const [memory, setMemory] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load initial case from localStorage or API
  useEffect(() => {
    const storedCaseId = localStorage.getItem('cc_case_id');
    if (storedCaseId) {
      setCaseId(storedCaseId);
    } else {
      // Try to fetch current case from API
      fetch('/api/cases/current')
        .then(r => r.json())
        .then(data => {
          if (data.id) {
            setCaseId(data.id);
          }
        })
        .catch(console.error);
    }
  }, []);

  const loadMemory = async (id: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/memory/${id}`);
      if (res.ok) {
        const data = await res.json();
        setMemory(data);
      } else {
        setMemory({});
      }
    } catch (e) {
      console.error('Failed to load memory', e);
      setMemory({});
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      localStorage.setItem('cc_case_id', caseId);
      loadMemory(caseId);
    }
  }, [caseId]);

  const value: CaseContextValue = {
    caseId,
    setCaseId,
    memory,
    refreshMemory: () => caseId && loadMemory(caseId),
    isLoading,
  };

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
};

export const useCaseContext = (): CaseContextValue => {
  const ctx = useContext(CaseContext);
  if (!ctx) {
    throw new Error('useCaseContext must be used within a CaseProvider');
  }
  return ctx;
};
