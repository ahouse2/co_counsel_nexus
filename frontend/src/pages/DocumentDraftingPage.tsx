import { useState } from 'react';
import { motion } from 'framer-motion';

export default function DocumentDraftingPage() {
  const [documentText, setDocumentText] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGetSuggestions = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/agents/drafting/suggestions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: documentText }),
      });

      if (!response.ok) {
        throw new Error(`Failed to get suggestions: ${response.statusText}`);
      }

      const result = await response.json();
      setSuggestions(result.suggestions);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-background-canvas text-text-primary h-screen p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="panel-shell"
      >
        <header>
          <h2>AI-Assisted Document Drafting</h2>
          <p className="panel-subtitle">Draft legal documents with the help of AI.</p>
        </header>
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2">
            <textarea
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
              className="w-full h-96 p-4 bg-background-surface border border-border rounded-lg"
              placeholder="Start writing your document..."
            />
          </div>
          <div>
            <button
              onClick={handleGetSuggestions}
              className="w-full bg-accent-violet-500 text-white py-2 px-4 rounded-lg hover:bg-accent-violet-600 transition-colors"
              disabled={isLoading}
            >
              {isLoading ? 'Getting Suggestions...' : 'Get Suggestions'}
            </button>
            {error && <p className="text-red-500 text-sm mt-2">Error: {error}</p>}
            <div className="mt-4">
              <h3 className="text-lg font-semibold">Suggestions</h3>
              <ul className="mt-2 space-y-2">
                {suggestions.map((suggestion, index) => (
                  <li key={index} className="bg-background-surface p-2 rounded-lg">
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}