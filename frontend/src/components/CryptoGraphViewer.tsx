import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface CryptoGraphViewerProps {
  mermaidDefinition: string;
}

const CryptoGraphViewer: React.FC<CryptoGraphViewerProps> = ({ mermaidDefinition }) => {
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mermaidRef.current && mermaidDefinition) {
      mermaid.initialize({ startOnLoad: false });
      mermaid.render('graphDiv', mermaidDefinition).then(({ svg }) => {
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = svg;
        }
      }).catch(error => {
        console.error("Mermaid rendering failed:", error);
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = `<p class="text-red-500">Failed to render graph: ${error.message}</p>`;
        }
      });
    }
  }, [mermaidDefinition]);

  return (
    <div className="p-4 border rounded-lg shadow-sm bg-gray-50">
      <h3 className="text-lg font-semibold mb-2">Cryptocurrency Transaction Graph</h3>
      {mermaidDefinition ? (
        <div ref={mermaidRef} className="mermaid-graph overflow-auto">
          {/* Mermaid diagram will be rendered here */}
        </div>
      ) : (
        <p className="text-sm text-gray-600">No graph definition available.</p>
      )}
    </div>
  );
};

export default CryptoGraphViewer;