import { useState, useRef, useCallback } from 'react';

// Upload state types
export interface FileUploadStatus {
    file: File;
    relativePath: string;
    status: 'pending' | 'uploading' | 'completed' | 'failed' | 'retrying';
    progress: number;
    retryCount: number;
    error?: string;
}

export interface UploadState {
    status: 'idle' | 'uploading' | 'paused' | 'completed' | 'failed';
    files: FileUploadStatus[];
    currentChunk: number;
    totalChunks: number;
    totalFiles: number;
    completedFiles: number;
    failedFiles: number;
    totalBytes: number;
    uploadedBytes: number;
    currentSpeed: number;
    startTime: number;
    pausedAt?: number;
}

const CHUNK_SIZE = 10; // Files per chunk
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second

// Helper: chunk array into smaller arrays
const chunkArray = <T,>(array: T[], size: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size));
    }
    return chunks;
};

// Helper: sleep function
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const useUploadManager = (uploadFn: (files: File[], paths: string[], chunkIndex: number, totalChunks: number, onProgress?: (progress: number) => void) => Promise<any>) => {
    const [state, setState] = useState<UploadState>({
        status: 'idle',
        files: [],
        currentChunk: 0,
        totalChunks: 0,
        totalFiles: 0,
        completedFiles: 0,
        failedFiles: 0,
        totalBytes: 0,
        uploadedBytes: 0,
        currentSpeed: 0,
        startTime: 0,
    });

    const pauseRequested = useRef(false);
    const cancelRequested = useRef(false);

    // Batch update helper
    const updateFilesStatus = useCallback((indices: number[], updates: Partial<FileUploadStatus>) => {
        setState(prev => ({
            ...prev,
            files: prev.files.map((f, i) =>
                indices.includes(i) ? { ...f, ...updates } : f
            )
        }));
    }, []);

    const uploadChunkWithRetry = async (
        files: File[],
        paths: string[],
        chunkIndex: number,
        totalChunks: number,
        fileIndices: number[]
    ): Promise<void> => {
        const chunkTotalBytes = files.reduce((sum, f) => sum + f.size, 0);
        let lastLoaded = 0;
        const startTime = Date.now();

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                // Mark files as uploading
                updateFilesStatus(fileIndices, {
                    status: attempt > 0 ? 'retrying' : 'uploading',
                    retryCount: attempt
                });

                await uploadFn(files, paths, chunkIndex, totalChunks, (progress) => {
                    // Progress callback (0 to 1)
                    const loaded = progress * chunkTotalBytes;
                    const delta = loaded - lastLoaded;
                    lastLoaded = loaded;

                    // Update speed and total uploaded bytes
                    const duration = (Date.now() - startTime) / 1000;
                    const speed = duration > 0 ? loaded / (1024 * 1024) / duration : 0; // MB/s

                    setState(prev => ({
                        ...prev,
                        uploadedBytes: prev.uploadedBytes + delta, // Accumulate delta
                        currentSpeed: speed
                    }));
                });

                // Mark files as completed
                updateFilesStatus(fileIndices, { status: 'completed', progress: 100 });

                setState(prev => ({
                    ...prev,
                    completedFiles: prev.completedFiles + files.length,
                }));

                return; // Success!

            } catch (error) {
                if (attempt === MAX_RETRIES) {
                    // Final failure
                    updateFilesStatus(fileIndices, {
                        status: 'failed',
                        error: error instanceof Error ? error.message : 'Upload failed'
                    });

                    setState(prev => ({
                        ...prev,
                        failedFiles: prev.failedFiles + files.length,
                    }));

                    throw error;
                }

                // Exponential backoff
                const delay = INITIAL_RETRY_DELAY * Math.pow(2, attempt);
                await sleep(delay);
            }
        }
    };

    const startUpload = async (fileList: FileList) => {
        const filesArray = Array.from(fileList);
        const chunks = chunkArray(filesArray, CHUNK_SIZE);

        const totalBytes = filesArray.reduce((sum, f) => sum + f.size, 0);

        setState({
            status: 'uploading',
            files: filesArray.map(f => ({
                file: f,
                relativePath: (f as any).webkitRelativePath || f.name,
                status: 'pending',
                progress: 0,
                retryCount: 0,
            })),
            currentChunk: 0,
            totalChunks: chunks.length,
            totalFiles: filesArray.length,
            completedFiles: 0,
            failedFiles: 0,
            totalBytes,
            uploadedBytes: 0,
            currentSpeed: 0,
            startTime: Date.now(),
        });

        pauseRequested.current = false;
        cancelRequested.current = false;

        try {
            for (let i = 0; i < chunks.length; i++) {
                if (pauseRequested.current) {
                    setState(prev => ({ ...prev, status: 'paused', pausedAt: Date.now(), currentChunk: i }));
                    return;
                }
                if (cancelRequested.current) {
                    setState(prev => ({ ...prev, status: 'idle' }));
                    return;
                }

                const chunk = chunks[i];
                const paths = chunk.map(f => (f as any).webkitRelativePath || f.name);
                const fileIndices = Array.from({ length: chunk.length }, (_, idx) => i * CHUNK_SIZE + idx);

                await uploadChunkWithRetry(chunk, paths, i, chunks.length, fileIndices);

                setState(prev => ({ ...prev, currentChunk: i + 1 }));
            }

            setState(prev => ({ ...prev, status: prev.failedFiles > 0 ? 'failed' : 'completed' }));

        } catch (error) {
            setState(prev => ({ ...prev, status: 'failed' }));
        }
    };

    const pause = useCallback(() => { pauseRequested.current = true; }, []);

    const resume = useCallback(() => {
        if (state.status !== 'paused') return;
        setState(prev => ({ ...prev, status: 'uploading', pausedAt: undefined }));
        pauseRequested.current = false;

        // Resume logic (simplified: restart current chunk loop)
        const chunks = chunkArray(state.files.map(f => f.file), CHUNK_SIZE);
        // ... (resume logic similar to startUpload loop starting from currentChunk)
        // For brevity, relying on the user to re-trigger or implementing full resume logic here is complex in one go.
        // But the original implementation had resume logic. I should preserve it or fix it.
        // Re-implementing resume loop:
        (async () => {
            try {
                for (let i = state.currentChunk; i < chunks.length; i++) {
                    if (pauseRequested.current || cancelRequested.current) return;
                    const chunk = chunks[i];
                    const paths = chunk.map(f => (f as any).webkitRelativePath || f.name);
                    const fileIndices = Array.from({ length: chunk.length }, (_, idx) => i * CHUNK_SIZE + idx);
                    await uploadChunkWithRetry(chunk, paths, i, chunks.length, fileIndices);
                    setState(prev => ({ ...prev, currentChunk: i + 1 }));
                }
                setState(prev => ({ ...prev, status: prev.failedFiles > 0 ? 'failed' : 'completed' }));
            } catch (error) {
                setState(prev => ({ ...prev, status: 'failed' }));
            }
        })();
    }, [state]);

    const cancel = useCallback(() => {
        cancelRequested.current = true;
        setState({ status: 'idle', files: [], currentChunk: 0, totalChunks: 0, totalFiles: 0, completedFiles: 0, failedFiles: 0, totalBytes: 0, uploadedBytes: 0, currentSpeed: 0, startTime: 0 });
    }, []);

    return { state, startUpload, pause, resume, cancel };
};
