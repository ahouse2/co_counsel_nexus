import { ReactNode, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface EvidenceModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function EvidenceModal({ title, onClose, children }: EvidenceModalProps): JSX.Element | null {
  const modalRoot = document.getElementById('modal-root');
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedRef = useRef<Element | null>(null);

  useEffect((): (() => void) | undefined => {
    if (!modalRoot) {
      return undefined;
    }
    previouslyFocusedRef.current = document.activeElement;
    const containerElement = document.createElement('div');
    containerElement.className = 'evidence-modal';
    modalRoot.appendChild(containerElement);
    setContainer(containerElement);
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        onClose();
      }
      if (event.key === 'Tab') {
        const scope = dialogRef.current ?? containerElement;
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
    containerElement.addEventListener('keydown', onKeyDown);
    requestAnimationFrame(() => {
      const focusTarget = dialogRef.current?.querySelector<HTMLElement>(
        'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'
      );
      focusTarget?.focus();
    });
    return () => {
      containerElement.removeEventListener('keydown', onKeyDown);
      if (modalRoot.contains(containerElement)) {
        modalRoot.removeChild(containerElement);
      }
      setContainer((current) => (current === containerElement ? null : current));
      if (previouslyFocusedRef.current instanceof HTMLElement) {
        previouslyFocusedRef.current.focus();
      }
    };
  }, [modalRoot, onClose]);

  if (!modalRoot || !container) {
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

  return createPortal(modalContent, container);
}
