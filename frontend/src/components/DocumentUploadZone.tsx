import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument } from '../services/document_api';

interface DocumentUploadZoneProps {
  caseId: string;
  onUploadSuccess: (response: any) => void;
  onUploadError: (error: any) => void;
}

const DocumentUploadZone: React.FC<DocumentUploadZoneProps> = ({ caseId, onUploadSuccess, onUploadError }) => {
  const [docType, setDocType] = useState<'my_documents' | 'opposition_documents'>('my_documents');
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    const file = acceptedFiles[0]; // Only handle one file for now

    try {
      const response = await uploadDocument(caseId, docType, file);
      onUploadSuccess(response);
    } catch (error) {
      onUploadError(error);
    } finally {
      setIsUploading(false);
    }
  }, [caseId, docType, onUploadSuccess, onUploadError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false, // Only allow single file uploads for now
  });

  return (
    <div className="p-4 border-2 border-dashed rounded-lg text-center">
      <div {...getRootProps()} className={`cursor-pointer ${isDragActive ? 'border-blue-500 bg-blue-100' : 'border-gray-300 bg-gray-50'} p-8 rounded-md`}>
        <input {...getInputProps()} />
        {
          isDragActive ?
            <p>Drop the files here ...</p> :
            <p>Drag 'n' drop some files here, or click to select files</p>
        }
        {isUploading && <p className="mt-2 text-blue-600">Uploading...</p>}
      </div>
      <div className="mt-4">
        <label htmlFor="docType" className="block text-sm font-medium text-gray-700">Document Type:</label>
        <select
          id="docType"
          name="docType"
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          value={docType}
          onChange={(e) => setDocType(e.target.value as 'my_documents' | 'opposition_documents')}
          disabled={isUploading}
        >
          <option value="my_documents">My Documents</option>
          <option value="opposition_documents">Opposition Documents</option>
        </select>
      </div>
    </div>
  );
};

export default DocumentUploadZone;
