import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ForensicAnalysisResult, CryptoTracingResult } from '@/services/forensics_api'; // Assuming these types exist
import { getForensicAnalysis, getCryptoTracing } from '@/services/forensics_api';
import { CryptoGraphViewer } from '@/components/CryptoGraphViewer'; // Assuming this component exists

interface ForensicsReportPageParams {
  caseId: string;
  docType: string;
  docId: string;
}

const ForensicsReportPage: React.FC = () => {
  const { caseId, docType, docId } = useParams<ForensicsReportPageParams>();
  const [forensicResults, setForensicResults] = useState<ForensicAnalysisResult | null>(null);
  const [cryptoTracingResults, setCryptoTracingResults] = useState<CryptoTracingResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      setLoading(true);
      setError(null);
      try {
        const forensicData = await getForensicAnalysis(caseId!, docType!, docId!);
        setForensicResults(forensicData);

        const cryptoData = await getCryptoTracing(caseId!, docType!, docId!);
        setCryptoTracingResults(cryptoData);
      } catch (err) {
        console.error('Failed to fetch forensic data:', err);
        setError('Failed to load forensic report. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (caseId && docType && docId) {
      fetchResults();
    }
  }, [caseId, docType, docId]);

  if (loading) {
    return <div className="p-4 text-center">Loading forensic report...</div>;
  }

  if (error) {
    return <div className="p-4 text-center text-red-500">{error}</div>;
  }

  if (!forensicResults && !cryptoTracingResults) {
    return <div className="p-4 text-center">No forensic or crypto tracing results found for this document.</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Forensic Report for Document: {docId}</h1>

      {forensicResults && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Forensic Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold mb-2">Overall Verdict: {forensicResults.overall_verdict}</p>
            <p><strong>Tamper Score:</strong> {forensicResults.tamper_score.score.toFixed(2)}</p>
            <p className="text-sm text-gray-500 mb-4">{forensicResults.tamper_score.details}</p>

            {forensicResults.ela_analysis && (
              <>
                <Separator className="my-4" />
                <h3 className="text-xl font-semibold mb-2">Error Level Analysis (ELA)</h3>
                <p><strong>ELA Score:</strong> {forensicResults.ela_analysis.ela_score.toFixed(2)}</p>
                <p className="text-sm text-gray-500">{forensicResults.ela_analysis.details}</p>
                {forensicResults.ela_analysis.ela_heatmap_url && (
                  <img src={forensicResults.ela_analysis.ela_heatmap_url} alt="ELA Heatmap" className="mt-2 max-w-full h-auto" />
                )}
              </>
            )}

            {/* Add more forensic analysis results here as they become available */}
          </CardContent>
        </Card>
      )}

      {cryptoTracingResults && (
        <Card>
          <CardHeader>
            <CardTitle>Cryptocurrency Tracing</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold mb-2">{cryptoTracingResults.details}</p>

            {cryptoTracingResults.wallets_found.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xl font-semibold mb-2">Wallets Found:</h3>
                <ul>
                  {cryptoTracingResults.wallets_found.map((wallet, index) => (
                    <li key={index} className="mb-1">
                      <strong>Address:</strong> {wallet.address} ({wallet.blockchain}, {wallet.currency}) - {wallet.is_valid ? 'Valid' : 'Invalid'}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {cryptoTracingResults.transactions_traced.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xl font-semibold mb-2">Transactions Traced:</h3>
                <ul>
                  {cryptoTracingResults.transactions_traced.map((tx, index) => (
                    <li key={index} className="mb-1 text-sm">
                      <strong>Tx ID:</strong> {tx.tx_id} <br />
                      <strong>From:</strong> {tx.sender} <br />
                      <strong>To:</strong> {tx.receiver} <br />
                      <strong>Amount:</strong> {tx.amount} {tx.currency} ({tx.blockchain}) <br />
                      <strong>Timestamp:</strong> {new Date(tx.timestamp).toLocaleString()}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {cryptoTracingResults.visual_graph_mermaid && (
              <div>
                <h3 className="text-xl font-semibold mb-2">Transaction Graph</h3>
                <CryptoGraphViewer mermaidDefinition={cryptoTracingResults.visual_graph_mermaid} />
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ForensicsReportPage;
