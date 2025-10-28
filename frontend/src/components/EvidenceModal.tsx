import { ReactNode, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface EvidenceModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function EvidenceModal({ title, onClose, children }: EvidenceModalProps): JSX.Element | null {
  const modalRoot = document.getElementById('modal-root');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedRef = useRef<Element | null>(null);

  useEffect((): (() => void) | undefined => {
    if (!modalRoot) {
      return undefined;
    }
    previouslyFocusedRef.current = document.activeElement;
    const container = document.createElement('div');
    container.className = 'evidence-modal';
    modalRoot.appendChild(container);
    containerRef.current = container;
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        onClose();
      }
      if (event.key === 'Tab') {
        const scope = dialogRef.current ?? container;
        const focusableElements = scope.querySelectorAll<HTMLElement>(
          'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) return;
        const first = focusableElements[0];
        const last = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    container.addEventListener('keydown', onKeyDown);
    requestAnimationFrame(() => {
      const focusTarget = dialogRef.current?.querySelector<HTMLElement>(
        'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'
      );
      focusTarget?.focus();
    });
    return () => {
      container.removeEventListener('keydown', onKeyDown);
      modalRoot.removeChild(container);
      if (previouslyFocusedRef.current instanceof HTMLElement) {
        previouslyFocusedRef.current.focus();
      }
    };
  }, [modalRoot, onClose]);

  if (!modalRoot || !containerRef.current) {
    return null;
  }

  const modalContent = (
    <div
      ref={dialogRef}
      className="evidence-modal__dialog"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <header>
        <h2>{title}</h2>
        <button type="button" onClick={onClose} aria-label="Close evidence panel">
          Close
        </button>
      </header>
      <div className="evidence-modal__body">{children}</div>
    </div>
  );

  return createPortal(modalContent, containerRef.current);
}
