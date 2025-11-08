import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Inbox, FolderOpen } from 'lucide-react';

interface FolderUploadProps {
  onFolderSelected: (files: File[]) => void;
}

const FolderUpload: React.FC<FolderUploadProps> = ({ onFolderSelected }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFolderSelected(acceptedFiles);
  }, [onFolderSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true, // Prevent opening file dialog on click
    // @ts-ignore
    webkitdirectory: true, // Enable folder selection
    directory: true, // Enable folder selection for newer browsers
  });

  return (
    <div
      {...getRootProps()}
      className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg cursor-pointer transition-colors duration-200
        ${isDragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 bg-gray-800 hover:border-gray-600'}`}
    >
      <input {...getInputProps()} />
      {isDragActive ? (
        <FolderOpen className="w-12 h-12 text-blue-400" />
      ) : (
        <Inbox className="w-12 h-12 text-gray-400" />
      )}
      <p className="mt-4 text-lg text-gray-300">
        Drag & drop a folder here, or <span className="text-blue-400 font-medium">click to select folder</span>
      </p>
      <p className="text-sm text-gray-500">Select an entire directory for ingestion</p>
    </div>
  );
};

export default FolderUpload;
