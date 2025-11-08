import React, { useState } from 'react';
import DocumentUploadZone from '../components/DocumentUploadZone';

interface UploadedDocument {
  doc_id: string;
  file_name: string;
  doc_type: string;
  ingestion_status: string;
  pipeline_result: string[];
}

const UploadEvidencePage: React.FC = () => {
  const [caseId, setCaseId] = useState('default-case-id'); // Placeholder for case ID
  const [uploadedDocuments, setUploadedDocuments] = useState<UploadedDocument[]>([]);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleUploadSuccess = (response: any) => {
    setUploadedDocuments((prevDocs) => [...prevDocs, {
      doc_id: response.data.doc_id,
      file_name: response.data.file_name,
      doc_type: response.data.doc_type,
      ingestion_status: response.data.ingestion_status,
      pipeline_result: response.data.pipeline_result,
    }]);
    setMessage({ type: 'success', text: response.message });
  };

  const handleUploadError = (error: any) => {
    console.error('Upload error:', error);
    setMessage({ type: 'error', text: `Upload failed: ${error.response?.data?.detail || error.message}` });
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Upload Evidence</h1>

      {message && (
        <div className={`p-3 mb-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message.text}
        </div>
      )}

      <div className="mb-4">
        <label htmlFor="caseId" className="block text-sm font-medium text-gray-700">Case ID:</label>
        <input
          type="text"
          id="caseId"
          className="mt-1 block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={caseId}
          onChange={(e) => setCaseId(e.target.value)}
        />
      </div>

      <DocumentUploadZone
        caseId={caseId}
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />

      <h2 className="text-xl font-bold mt-8 mb-4">Uploaded Documents</h2>
      {
        uploadedDocuments.length === 0 ? (
          <p>No documents uploaded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File Name</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categories</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Doc ID</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {uploadedDocuments.map((doc) => (
                  <tr key={doc.doc_id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.file_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.doc_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.ingestion_status}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.pipeline_result.join(', ')}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.doc_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }
    </div>
  );
};

export default UploadEvidencePage;