import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
import { Graph3DScene } from "./Graph3DScene"
import { Search, Filter, ZoomIn, ZoomOut, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

interface GraphNode {
  id: string
  label: string
  x: number
  y: number
  z: number
  cluster: string
  connections: string[]
}

const GraphExplorerPanel: React.FC = () => {
  // Sample graph data - in a real app this would come from an API
  const [nodes, setNodes] = React.useState<GraphNode[]>([
    { id: "1", label: "Evidence A", x: -2, y: 0, z: 0, cluster: "evidence", connections: ["2", "3"] },
    { id: "2", label: "Person B", x: 2, y: 1, z: 1, cluster: "person", connections: ["1", "4"] },
    { id: "3", label: "Document C", x: 0, y: -1, z: -1, cluster: "document", connections: ["1", "4"] },
    { id: "4", label: "Event D", x: 1, y: 0, z: 2, cluster: "event", connections: ["2", "3"] },
  ])

  const handleNodeClick = (node: GraphNode) => {
    console.log("Node clicked:", node)
    // In a real app, this would open a detail view or highlight related nodes
  }

  const handleSearch = () => {
    // Implement search functionality
  }

  const handleFilter = () => {
    // Implement filter functionality
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <Card className="bg-background-panel border-border-subtle shadow-cyan-sm rounded-2xl overflow-hidden">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="text-text-primary font-display text-xl">
              3D Graph Explorer
            </CardTitle>
            <div className="flex flex-wrap gap-2">
              <Button 
                variant="cinematic" 
                size="sm"
                onClick={handleSearch}
                className="flex items-center gap-2"
              >
                <Search className="w-4 h-4" />
                Search
              </Button>
              <Button 
                variant="cinematic" 
                size="sm"
                onClick={handleFilter}
                className="flex items-center gap-2"
              >
                <Filter className="w-4 h-4" />
                Filter
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary"
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary"
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary"
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <p className="text-text-secondary text-sm mt-2">
            Interactive 3D visualization of evidence connections with neon-glass nodes
          </p>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-[500px] w-full relative">
            <Graph3DScene 
              nodes={nodes} 
              onNodeClick={handleNodeClick}
              className="rounded-b-2xl"
            />
            
            {/* Cinematic HUD overlay */}
            <div className="absolute inset-0 pointer-events-none">
              {/* Top metrics bar */}
              <div className="absolute top-4 left-4 right-4 flex justify-between">
                <div className="bg-background-overlay/80 backdrop-blur-sm border border-border-subtle rounded-lg p-3 shadow-cyan-xs pointer-events-auto">
                  <h4 className="text-text-primary text-sm font-medium mb-2">Graph Metrics</h4>
                  <div className="flex gap-4">
                    <div>
                      <p className="text-text-secondary text-xs">Nodes</p>
                      <p className="text-text-primary font-medium">{nodes.length}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary text-xs">Connections</p>
                      <p className="text-text-primary font-medium">{nodes.reduce((acc, node) => acc + node.connections.length, 0)}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary text-xs">Clusters</p>
                      <p className="text-text-primary font-medium">3</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-background-overlay/80 backdrop-blur-sm border border-border-subtle rounded-lg p-3 shadow-cyan-xs pointer-events-auto">
                  <h4 className="text-text-primary text-sm font-medium mb-2">View Controls</h4>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="flex items-center gap-2 border-border-subtle text-text-secondary"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="flex items-center gap-2 border-border-subtle text-text-secondary"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="flex items-center gap-2 border-border-subtle text-text-secondary"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Side filter panel */}
              <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-background-overlay/80 backdrop-blur-sm border border-border-subtle rounded-lg p-3 shadow-cyan-xs pointer-events-auto">
                <h4 className="text-text-primary text-sm font-medium mb-2">Filters</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent-cyan-500"></div>
                    <span className="text-text-secondary text-xs">Evidence</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent-violet-500"></div>
                    <span className="text-text-secondary text-xs">People</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent-gold"></div>
                    <span className="text-text-secondary text-xs">Documents</span>
                  </div>
                </div>
              </div>
              
              {/* Search bar */}
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-background-overlay/80 backdrop-blur-sm border border-border-subtle rounded-lg p-2 shadow-cyan-xs pointer-events-auto w-80">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                  <input
                    type="text"
                    placeholder="Search nodes..."
                    className="pl-10 pr-4 py-2 bg-background-surface border border-border-subtle rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan-500/50 w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export { GraphExplorerPanel }