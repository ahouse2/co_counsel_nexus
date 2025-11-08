import axios from 'axios';

const API_BASE_URL = '/api/documents'; // Adjust if your API is hosted elsewhere

interface UploadDocumentResponse {
  message: string;
  data: {
    doc_id: string;
    version: string;
    case_id: string;
    doc_type: string;
    file_name: string;
    ingestion_status: string;
    pipeline_result: string[]; // Categories from pipeline
  };
}

export const uploadDocument = async (
  caseId: string,
  docType: 'my_documents' | 'opposition_documents',
  file: File
): Promise<UploadDocumentResponse> => {
  const formData = new FormData();
  formData.append('case_id', caseId);
  formData.append('doc_type', docType);
  formData.append('file', file);

  const response = await axios.post<UploadDocumentResponse>(`${API_BASE_URL}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

interface DocumentContentResponse {
  content: string;
}

export const getDocument = async (
  caseId: string,
  docType: 'my_documents' | 'opposition_documents',
  docId: string,
  version?: string
): Promise<DocumentContentResponse> => {
  const params = version ? { version } : {};
  const response = await axios.get<DocumentContentResponse>(`${API_BASE_URL}/${caseId}/${docType}/${docId}`, { params });
  return response.data;
};

interface DocumentVersionsResponse {
  versions: string[];
}

export const listDocumentVersions = async (
  caseId: string,
  docType: 'my_documents' | 'opposition_documents',
  docId: string
): Promise<string[]> => {
  const response = await axios.get<string[]>(`${API_BASE_URL}/${caseId}/${docType}/${docId}/versions`);
  return response.data;
};

export const deleteDocument = async (
  caseId: string,
  docType: 'my_documents' | 'opposition_documents',
  docId: string,
  version?: string
): Promise<{ message: string }> => {
  const params = version ? { version } : {};
  const response = await axios.delete<{ message: string }>(`${API_BASE_URL}/${caseId}/${docType}/${docId}`, { params });
  return response.data;
};
