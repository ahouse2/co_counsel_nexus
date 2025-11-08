import { useState } from 'react';
import { SectionId } from '@/components/layout/Sidebar';

export const useAppLayout = () => {
  const [activeSection, setActiveSection] = useState<SectionId>('evidence');

  return {
    activeSection,
    setActiveSection,
  };
};
