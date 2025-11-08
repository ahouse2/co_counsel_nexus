import React, { useState, useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { Loader2, GitGraph, Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

interface GraphNode {
  id: string;
  label: string;
  title?: string;
  group?: string;
  color?: string;
}

interface GraphEdge {
  from: string;
  to: string;
  label?: string;
  title?: string;
  arrows?: string;
  color?: string;
}

const KnowledgeGraphViewer: React.FC = () => {
  const networkRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes] = useState<DataSet<GraphNode>>(new DataSet());
  const [edges, setEdges] = useState<DataSet<GraphEdge>>(new DataSet());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchNodeId, setSearchNodeId] = useState('');
  const { toast } = useToast();

  useEffect(() => {
    if (networkRef.current) {
      const data = { nodes, edges };
      const options = {
        nodes: {
          shape: 'dot',
          size: 16,
          font: { size: 12, color: '#ffffff' },
          borderWidth: 2,
        },
        edges: {
          width: 1,
          arrows: 'to',
          font: { size: 10, color: '#ffffff', align: 'middle' },
          color: { inherit: 'from' },
        },
        physics: { enabled: true, stabilization: { iterations: 2000 } },
        interaction: { navigationButtons: true, keyboard: true },
        layout: { hierarchical: false },
      };
      const network = new Network(networkRef.current, data, options);

      network.on("click", (properties) => {
        if (properties.nodes.length > 0) {
          const nodeId = properties.nodes[0];
          const clickedNode = nodes.get(nodeId);
          if (clickedNode) {
            toast({
              title: `Node: ${clickedNode.label}`,
              description: clickedNode.title || `ID: ${clickedNode.id}`, 
            });
          }
        }
      });

      return () => {
        network.destroy();
      };
    }
  }, [nodes, edges, toast]);

  const fetchGraphData = async (nodeId?: string) => {
    setLoading(true);
    setError(null);
    try {
      // Placeholder for fetching graph data from backend
      // Replace with actual API calls to /graph/neighbor/{nodeId} or /graph/subgraph
      let fetchedNodes: GraphNode[] = [];
      let fetchedEdges: GraphEdge[] = [];

      if (nodeId) {
        // Simulate fetching neighbors for a specific node
        fetchedNodes = [
          { id: nodeId, label: `Node ${nodeId}`, group: 'focus' },
          { id: 'A', label: 'Entity A', group: 'related' },
          { id: 'B', label: 'Entity B', group: 'related' },
        ];
        fetchedEdges = [
          { from: nodeId, to: 'A', label: 'RELATES_TO' },
          { from: 'A', to: 'B', label: 'HAS_PROPERTY' },
        ];
      } else {
        // Simulate fetching a general subgraph
        fetchedNodes = [
          { id: '1', label: 'Document 1', group: 'document' },
          { id: '2', label: 'Document 2', group: 'document' },
          { id: 'PersonX', label: 'John Doe', group: 'person' },
          { id: 'CompanyY', label: 'Acme Corp', group: 'organization' },
          { id: 'ContractZ', label: 'Sales Contract', group: 'contract' },
        ];
        fetchedEdges = [
          { from: '1', to: 'PersonX', label: 'MENTIONS' },
          { from: '1', to: 'CompanyY', label: 'MENTIONS' },
          { from: 'PersonX', to: 'ContractZ', label: 'SIGNED' },
          { from: 'CompanyY', to: 'ContractZ', label: 'PART_OF' },
          { from: '2', to: 'PersonX', label: 'REFERENCES' },
        ];
      }

      setNodes(new DataSet(fetchedNodes));
      setEdges(new DataSet(fetchedEdges));

    } catch (err) {
      console.error("Failed to fetch graph data:", err);
      setError("Failed to load graph. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  const handleSearch = () => {
    if (searchNodeId.trim()) {
      fetchGraphData(searchNodeId.trim());
    } else {
      fetchGraphData(); // Reset to general view if search is empty
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-400">Loading knowledge graph...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-full text-red-500">
        <p>{error}</p>
      </div>
    );
    }

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-gray-100">
      <Card className="bg-gray-800 border-gray-700 shadow-lg">
        <CardHeader className="border-b border-gray-700">
          <CardTitle className="flex items-center text-blue-400">
            <GitGraph className="mr-2 h-6 w-6" /> Knowledge Graph Visualization
          </CardTitle>
          <p className="text-sm text-gray-400">Explore entities and their relationships.</p>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex space-x-2 mb-4">
            <Input
              type="text"
              placeholder="Search for a node ID..."
              value={searchNodeId}
              onChange={(e) => setSearchNodeId(e.target.value)}
              className="flex-grow bg-gray-700 border-gray-600 text-gray-100 placeholder-gray-400"
            />
            <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700 text-white">
              <Search className="mr-2 h-4 w-4" /> Search
            </Button>
            <Button onClick={() => { setSearchNodeId(''); fetchGraphData(); }} variant="outline" className="text-gray-300 border-gray-600 hover:bg-gray-700">
              Reset View
            </Button>
          </div>
          <div ref={networkRef} className="w-full h-[700px] border border-gray-700 rounded-md bg-gray-900" />
        </CardContent>
      </Card>
    </div>
  );
};

export default KnowledgeGraphViewer;
