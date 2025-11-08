import { motion } from 'framer-motion';
import React, { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  const handleFileUpload = useCallback(async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    setUploadedFile(file);
    setError(null);

    const documentId = uuidv4();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_id', documentId);

    try {
      const response = await fetch('/api/ingestion', {
        method: 'POST',
        body: formData,
        // You might need to implement a custom progress tracking for fetch or use a library like axios
        // For simplicity, progress is simulated here.
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      // Simulate progress
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        setUploadProgress(progress);
        if (progress >= 100) {
          clearInterval(interval);
          setIsUploading(false);
        }
      }, 200);

      const result = await response.json();
      console.log('Upload successful:', result);
      // Optionally, poll for ingestion status using /ingestion/{document_id}/status
    } catch (err: any) {
      setError(err.message);
      setIsUploading(false);
      setUploadProgress(0);
    }
  }, []);

  const zoneClassName = `upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''} ${uploadedFile && !isUploading && !error ? 'complete' : ''}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
      className="evidence-upload"
    >
      <div className="upload-intro">
        <h2>Evidence Upload & File Intelligence</h2>
        <p>Drag and drop files for AI analysis and auto-tagging.</p>
      </div>
      <div
        className={zoneClassName}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => document.getElementById('fileInput')?.click()}
      >
        <input
          type="file"
          id="fileInput"
          className="hidden"
          onChange={handleFileInputChange}
        />
        <div className="upload-copy">
          <div className="upload-icon">📁</div>
          <p className="upload-title">Drag & Drop or Browse Files</p>
          <p className="upload-subtitle">{uploadedFile ? uploadedFile.name : 'Max size 50MB'}</p>
          {isUploading && (
            <div className="progress-cinematic mt-2">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
            </div>
          )}
          {error && <p className="text-red-500 text-sm mt-2">Error: {error}</p>}
        </div>
        <div className="upload-ring">
          <div className="ring-glow"></div>
        </div>
      </div>
      {uploadedFile && !isUploading && !error && (
        <div className="uploaded-files">
          <div className="uploaded-file">
            <header>
              <span className="file-name">{uploadedFile.name}</span>
              <span className="file-size">{(uploadedFile.size / 1024 / 1024).toFixed(2)} MB</span>
            </header>
            <p className="text-sm text-gray-400">File uploaded successfully. Awaiting AI analysis...</p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
