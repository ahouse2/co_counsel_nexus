import React, { useEffect, useState } from 'react';
import AgentLiveGraph from './AgentLiveGraph';

type Team = {
  id: string;
  name: string;
  status: string;
  members: string[];
};

export default function AgentConsole(): JSX.Element {
  const [teams, setTeams] = useState<Team[]>([]);

  useEffect(() => {
    fetch('/api/agents/status')
      .then((r) => r.json())
      .then((data) => setTeams(data as Team[]))
      .catch(() => setTeams([]));
  }, []);

  return (
    <div className="p-6 space-y-6 h-full overflow-hidden flex flex-col">
      <div>
        <h2 className="text-2xl font-light tracking-tight text-white">Agent Console</h2>
        <p className="text-zinc-400">Live view of agent teams and neural activity</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Left Column: Team Status */}
        <div className="lg:col-span-2 overflow-y-auto pr-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {teams.map((t) => (
              <div key={t.id} className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/50">
                <div className="flex justify-between items-center mb-2">
                  <strong className="text-zinc-100">{t.name}</strong>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    t.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-700/50 text-zinc-400'
                  }`}>
                    {t.status}
                  </span>
                </div>
                <div className="text-xs text-zinc-500 mb-2">
                  Members: {t.members.length}
                </div>
                <ul className="space-y-1">
                  {t.members.map((m) => (
                    <li key={m} className="text-xs text-zinc-300 flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-zinc-600" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Live Graph */}
        <div className="h-full min-h-[400px]">
          <AgentLiveGraph />
        </div>
      </div>
    </div>
  );
}
