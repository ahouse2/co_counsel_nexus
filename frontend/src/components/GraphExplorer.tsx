import { motion } from 'framer-motion';
import React, { useState, useEffect } from 'react';

interface GraphNode {
  id: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function GraphExplorer() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError(null);
        // For demonstration, using a hardcoded node_id. In a real app, this would be dynamic.
        const response = await fetch('/api/graph/neighbors/some_hardcoded_node_id');
        if (!response.ok) {
          throw new Error(`Failed to fetch graph data: ${response.statusText}`);
        }
        const data = await response.json();
        // Assuming data structure matches GraphNeighborResponse and can be mapped to GraphData
        setGraphData({
          nodes: data.nodes.map((node: any) => ({ id: node.id, label: node.label })),
          edges: data.edges.map((edge: any) => ({ source: edge.source, target: edge.target })),
        });
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, []);

  return (
    <motion.div
      className="bg-[#1a1a1f] rounded-xl p-6 border border-[#2a2a2f] backdrop-blur-md shadow-[0_0_20px_#3b82f688]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
    >
      <h2 className="text-lg font-medium mb-2">Graph Explorer</h2>
      <div className="h-48 bg-black rounded-lg flex items-center justify-center text-gray-500">
        {loading && <span>Loading Graph...</span>}
        {error && <span className="text-red-500">Error: {error}</span>}
        {graphData && graphData.nodes.length > 0 && (
          <div>
            <h3>Nodes:</h3>
            <ul>
              {graphData.nodes.map((node) => (
                <li key={node.id}>{node.label} ({node.id})</li>
              ))}
            </ul>
            <h3>Edges:</h3>
            <ul>
              {graphData.edges.map((edge, index) => (
                <li key={index}>{edge.source} {'->'} {edge.target}</li>
              ))}
            </ul>
          </div>
        )}
        {!loading && !error && (!graphData || graphData.nodes.length === 0) && (
          <span>No Graph Data Available</span>
        )}
      </div>
    </motion.div>
  );
}
