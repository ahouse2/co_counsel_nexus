import React, { useState, useEffect } from 'react';
import { BarChart, TrendingUp, Lightbulb, Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface GraphStrategyBrief {
  generated_at: string;
  summary: string;
  focus_nodes: Array<{ id: string; label: string; type: string }>;
  argument_map: Array<any>; // Simplified for now
  contradictions: Array<any>; // Simplified for now
  leverage_points: Array<{ node: { id: string; label: string; type: string }; influence: number; connections: number; reason: string }>;
}

interface PredictiveOutcome {
  predicted_outcome: string;
  probabilities: { [key: string]: number };
  summary: string;
  strategy_brief: GraphStrategyBrief;
}

interface StrategicRecommendations {
  predicted_outcome: string;
  recommendations: string[];
  prediction_details: PredictiveOutcome;
}

const LegalDashboard: React.FC = () => {
  const [question, setQuestion] = useState("What are the key arguments in the contract dispute case?");
  const [focusNodes, setFocusNodes] = useState<string[]>(["ContractZ", "CompanyY"]);
  const [strategyBrief, setStrategyBrief] = useState<GraphStrategyBrief | null>(null);
  const [predictiveOutcome, setPredictiveOutcome] = useState<PredictiveOutcome | null>(null);
  const [strategicRecommendations, setStrategicRecommendations] = useState<StrategicRecommendations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Placeholder for fetching Legal Theory (Strategy Brief)
      // Replace with actual API call to /legal-theory/synthesize
      const mockStrategyBrief: GraphStrategyBrief = {
        generated_at: new Date().toISOString(),
        summary: "Key arguments revolve around contract clauses and company obligations.",
        focus_nodes: [
          { id: "ContractZ", label: "Sales Contract", type: "Contract" },
          { id: "CompanyY", label: "Acme Corp", type: "Organization" },
        ],
        argument_map: [],
        contradictions: [
          { source: { label: "Clause A" }, target: { label: "Clause B" }, relation: "CONTRADICTS", documents: ["doc1"] },
        ],
        leverage_points: [
          { node: { id: "PersonX", label: "John Doe", type: "Person" }, influence: 0.8, connections: 15, reason: "John Doe is connected to 15 node(s), linked to 3 document(s)." },
        ],
      };
      setStrategyBrief(mockStrategyBrief);

      // Placeholder for fetching Predictive Analytics
      // Replace with actual API call to /predictive-analytics/outcome
      const mockPredictiveOutcome: PredictiveOutcome = {
        predicted_outcome: "settlement",
        probabilities: { favorable: 0.3, unfavorable: 0.2, settlement: 0.5 },
        summary: "Based on the synthesized legal theories and available evidence, the predicted outcome is settlement with the following probabilities: favorable: 0.30, unfavorable: 0.20, settlement: 0.50.",
        strategy_brief: mockStrategyBrief,
      };
      setPredictiveOutcome(mockPredictiveOutcome);

      // Placeholder for fetching Strategic Recommendations
      // Replace with actual API call to /strategic-recommendations/get
      const mockStrategicRecommendations: StrategicRecommendations = {
        predicted_outcome: "settlement",
        recommendations: [
          "Prepare for negotiation by understanding key arguments and potential compromises.",
          "Be aware of contradictions that could impact negotiation.",
          "Consider the following focus nodes: [Sales Contract, Acme Corp]",
          "Key leverage points: [John Doe]",
        ],
        prediction_details: mockPredictiveOutcome,
      };
      setStrategicRecommendations(mockStrategicRecommendations);

    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      setError("Failed to load dashboard. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [question, focusNodes]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <BarChart className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-400">Loading legal dashboard...</span>
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
            <Scale className="mr-2 h-6 w-6" /> Legal Theory & Strategy Dashboard
          </CardTitle>
          <p className="text-sm text-gray-400">Insights for case outcomes and strategic planning.</p>
        </CardHeader>
        <CardContent className="pt-6">
          <Tabs defaultValue="theory" className="w-full">
            <TabsList className="grid w-full grid-cols-3 bg-gray-700">
              <TabsTrigger value="theory">Legal Theory</TabsTrigger>
              <TabsTrigger value="predictive">Predictive Analytics</TabsTrigger>
              <TabsTrigger value="strategic">Strategic Recommendations</TabsTrigger>
            </TabsList>
            <TabsContent value="theory" className="mt-4">
              <Card className="bg-gray-900 border-gray-700">
                <CardHeader>
                  <CardTitle className="flex items-center text-green-400"><Lightbulb className="mr-2 h-5 w-5" /> Legal Theory Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-200 mb-4">{strategyBrief?.summary}</p>
                  <h4 className="text-lg font-semibold text-gray-300">Focus Nodes:</h4>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {strategyBrief?.focus_nodes.map(node => (
                      <Badge key={node.id} variant="outline" className="bg-blue-600 text-white border-blue-600">
                        {node.label} ({node.type})
                      </Badge>
                    ))}
                  </div>
                  <h4 className="text-lg font-semibold text-gray-300 mt-4">Contradictions:</h4>
                  <ScrollArea className="h-[150px] w-full rounded-md border border-gray-700 p-4 bg-gray-800 mt-2">
                    {strategyBrief?.contradictions && strategyBrief.contradictions.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1 text-gray-200">
                        {strategyBrief.contradictions.map((contra, index) => (
                          <li key={index}>{contra.source.label} CONTRADICTS {contra.target.label}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-400">No significant contradictions identified.</p>
                    )}
                  </ScrollArea>
                  <h4 className="text-lg font-semibold text-gray-300 mt-4">Leverage Points:</h4>
                  <ScrollArea className="h-[150px] w-full rounded-md border border-gray-700 p-4 bg-gray-800 mt-2">
                    {strategyBrief?.leverage_points && strategyBrief.leverage_points.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1 text-gray-200">
                        {strategyBrief.leverage_points.map((lp, index) => (
                          <li key={index}>{lp.node.label} (Influence: {lp.influence.toFixed(2)}, Connections: {lp.connections}) - {lp.reason}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-400">No significant leverage points identified.</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="predictive" className="mt-4">
              <Card className="bg-gray-900 border-gray-700">
                <CardHeader>
                  <CardTitle className="flex items-center text-yellow-400"><TrendingUp className="mr-2 h-5 w-5" /> Predictive Outcome</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-200 mb-4">{predictiveOutcome?.summary}</p>
                  <h4 className="text-lg font-semibold text-gray-300">Probabilities:</h4>
                  <div className="space-y-3 mt-2">
                    {predictiveOutcome?.probabilities && Object.entries(predictiveOutcome.probabilities).map(([outcome, prob]) => (
                      <div key={outcome} className="flex items-center gap-2">
                        <span className="w-24 text-gray-200 capitalize">{outcome}:</span>
                        <Progress value={prob * 100} className="w-full h-3 bg-gray-700" indicatorColor={outcome === predictiveOutcome.predicted_outcome ? "bg-green-500" : "bg-blue-500"} />
                        <span className="w-10 text-right text-gray-200">{(prob * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="strategic" className="mt-4">
              <Card className="bg-gray-900 border-gray-700">
                <CardHeader>
                  <CardTitle className="flex items-center text-purple-400"><Lightbulb className="mr-2 h-5 w-5" /> Strategic Recommendations</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-200 mb-4">Predicted Outcome: <Badge className="capitalize bg-green-600 text-white">{strategicRecommendations?.predicted_outcome}</Badge></p>
                  <h4 className="text-lg font-semibold text-gray-300">Recommendations:</h4>
                  <ScrollArea className="h-[300px] w-full rounded-md border border-gray-700 p-4 bg-gray-800 mt-2">
                    {strategicRecommendations?.recommendations && strategicRecommendations.recommendations.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-2 text-gray-200">
                        {strategicRecommendations.recommendations.map((rec, index) => (
                          <li key={index}>{rec}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-400">No specific recommendations generated.</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default LegalDashboard;
