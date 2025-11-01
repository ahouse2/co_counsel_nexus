import {
  useCallback,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react';

type UploadState = 'idle' | 'dragging' | 'uploading' | 'complete' | 'error';

interface UploadedFile {
  id: string;
  name: string;
  size: string;
  status: UploadState;
  aiSummary: string;
}

const initialFiles: UploadedFile[] = [
  {
    id: 'exhibit-a',
    name: 'Exhibit A - Financial Summary.pdf',
    size: '4.2 MB',
    status: 'complete',
    aiSummary: 'Highlights fraudulent transfers, auto-tagged for privilege hold, contradiction risk low.',
  },
  {
    id: 'deposition-clip',
    name: 'Deposition_Clip_Witness03.mp4',
    size: '68 MB',
    status: 'complete',
    aiSummary: 'Key admissions detected at 02:14, cross-exam vulnerability flagged for rebuttal.',
  },
];

export function EvidenceUploadZone(): JSX.Element {
  const [files, setFiles] = useState<UploadedFile[]>(initialFiles);
  const [state, setState] = useState<UploadState>('idle');
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setState('uploading');
    const dropped = Array.from(event.dataTransfer.files).map<UploadedFile>((file) => ({
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
      status: 'complete',
      aiSummary: 'AI summary pending — generating timeline placement and privilege check.',
    }));
    setTimeout(() => {
      setFiles((current) => [...dropped, ...current]);
      setState('complete');
      setTimeout(() => setState('idle'), 2400);
    }, 850);
  }, []);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (state !== 'dragging') {
      setState('dragging');
    }
  }, [state]);

  const handleDragLeave = useCallback(() => {
    setState('idle');
  }, []);

  const handleBrowse = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files;
    if (!selected) return;
    setState('uploading');
    const added = Array.from(selected).map<UploadedFile>((file) => ({
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
      status: 'complete',
      aiSummary: 'AI summary pending — generating timeline placement and privilege check.',
    }));
    setTimeout(() => {
      setFiles((current) => [...added, ...current]);
      setState('complete');
      setTimeout(() => setState('idle'), 2400);
    }, 850);
  }, []);

  return (
    <section className="evidence-upload" aria-labelledby="evidence-upload-title">
      <div className="upload-intro">
        <h2 id="evidence-upload-title">Evidence Upload &amp; Intelligence</h2>
        <p>
          Drop files into the neon field — Co-Counsel processes provenance, contradictions, and privilege in
          seconds.
        </p>
      </div>
      <div
        className={`upload-zone ${state}`}
        role="button"
        tabIndex={0}
        aria-label="Upload evidence"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onKeyDown={(event: KeyboardEvent<HTMLDivElement>) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handleBrowse();
          }
        }}
        onClick={handleBrowse}
      >
        <div className="upload-ring" aria-hidden>
          <div className="ring-glow" />
        </div>
        <div className="upload-copy">
          <span className="upload-icon" aria-hidden>
            ⬆
          </span>
          <p className="upload-title">Drop files or tap to select</p>
          <p className="upload-subtitle">Encrypted intake, AI summaries, privilege sweeps</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          aria-hidden="true"
          tabIndex={-1}
          onChange={handleFileChange}
        />
      </div>
      <div className="uploaded-files" aria-live="polite">
        {files.map((file) => (
          <article key={file.id} className="uploaded-file" data-status={file.status}>
            <header>
              <span className="file-name">{file.name}</span>
              <span className="file-size">{file.size}</span>
            </header>
            <p>{file.aiSummary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
