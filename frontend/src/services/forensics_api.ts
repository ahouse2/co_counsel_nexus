import axios from 'axios';

const API_BASE_URL = '/api/v1'; // Adjust if your API is hosted elsewhere

// --- Forensic Analysis Types ---
export interface TamperScoreResult {
  score: number;
  details: string;
  flags?: string[];
}

export interface ElaResult {
  ela_score: number;
  details: string;
  ela_heatmap_url?: string;
}

export interface CloneSplicingResult {
  detected: boolean;
  details: string;
  regions?: string[];
}

export interface FontObjectAnalysisResult {
  inconsistencies_detected: boolean;
  details: string;
  anomalies?: string[];
}

export interface AntiScanAlterRescanResult {
  detected: boolean;
  details: string;
}

export interface ForensicAnalysisResult {
  document_id: string;
  tamper_score: TamperScoreResult;
  ela_analysis?: ElaResult;
  clone_splicing_detection?: CloneSplicingResult;
  font_object_analysis?: FontObjectAnalysisResult;
  anti_scan_alter_rescan?: AntiScanAlterRescanResult;
  overall_verdict: string;
}

// --- Crypto Tracing Types ---
export interface WalletAddress {
  address: string;
  blockchain: string;
  currency: string;
  is_valid: boolean;
}

export interface Transaction {
  tx_id: string;
  sender: string;
  receiver: string;
  amount: number;
  currency: string;
  timestamp: string;
  blockchain: string;
}

export interface CryptoTracingResult {
  wallets_found: WalletAddress[];
  transactions_traced: Transaction[];
  visual_graph_mermaid?: string;
  details: string;
}

// --- API Calls ---
export const getForensicAnalysis = async (
  caseId: string,
  docType: string,
  docId: string,
  version?: string
): Promise<ForensicAnalysisResult> => {
  const response = await axios.get<ForensicAnalysisResult>(
    `${API_BASE_URL}/cases/${caseId}/${docType}/${docId}/forensics`,
    { params: { version } }
  );
  return response.data;
};

export const getCryptoTracing = async (
  caseId: string,
  docType: string,
  docId: string,
  version?: string
): Promise<CryptoTracingResult> => {
  const response = await axios.get<CryptoTracingResult>(
    `${API_BASE_URL}/cases/${caseId}/${docType}/${docId}/crypto-tracing`,
    { params: { version } }
  );
  return response.data;
};
