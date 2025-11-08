import { motion } from 'framer-motion';
import React, { useState, useEffect } from 'react';

interface Scenario {
  id: string;
  name: string;
  description: string;
}

export function MockTrialArena() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/scenarios');
        if (!response.ok) {
          throw new Error(`Failed to fetch scenarios: ${response.statusText}`);
        }
        const data = await response.json();
        setScenarios(data.scenarios);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchScenarios();
  }, []);

  const handleRunScenario = async () => {
    if (!selectedScenario) return;
    // Placeholder for running a scenario
    console.log(`Running scenario: ${selectedScenario.name}`);
    // In a real implementation, this would call POST /scenarios/run
  };

  return (
    <motion.div
      className="bg-[#1a1a1f] rounded-xl p-6 border border-[#2a2a2f] backdrop-blur-md shadow-[0_0_20px_#ff000088]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.4, ease: "easeOut" }}
    >
      <h2 className="text-lg font-medium mb-2">Mock Trial Arena</h2>
      {loading && <span>Loading Scenarios...</span>}
      {error && <span className="text-red-500">Error: {error}</span>}
      {!loading && !error && scenarios.length > 0 && (
        <div className="scenario-selection">
          <h3>Available Scenarios:</h3>
          <select
            onChange={(e) => {
              const scenarioId = e.target.value;
              setSelectedScenario(scenarios.find(s => s.id === scenarioId) || null);
            }}
            className="w-full p-2 rounded bg-gray-800 text-white border border-gray-700"
          >
            <option value="">Select a Scenario</option>
            {scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.name}
              </option>
            ))}
          </select>
          {selectedScenario && (
            <div className="mt-4 p-4 bg-gray-800 rounded">
              <h4>{selectedScenario.name}</h4>
              <p>{selectedScenario.description}</p>
              <button
                onClick={handleRunScenario}
                className="mt-2 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
              >
                Run Scenario
              </button>
            </div>
          )}
        </div>
      )}
      {!loading && !error && scenarios.length === 0 && (
        <span>No scenarios available.</span>
      )}

      <div className="mt-4 text-xs text-gray-400">Live video + transcript stream (placeholder)</div>
    </motion.div>
  );
}
