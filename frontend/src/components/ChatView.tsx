import { FormEvent, useEffect, useRef, useState } from 'react';
import type { AnchorHTMLAttributes } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useQueryContext } from '@/context/QueryContext';
import { ChatMessage, Citation } from '@/types';
import { VoiceConsole } from '@/components/VoiceConsole';

const markdownComponents: Components = {
  a: (props: AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),
};

export function ChatView(): JSX.Element {
  const { messages, sendMessage, retryLast, loading, error, setActiveCitation } = useQueryContext();
  const [prompt, setPrompt] = useState('');
  const listRef = useRef<HTMLDivElement | null>(null);
  const liveRegionRef = useRef<HTMLDivElement | null>(null);

  useEffect((): void => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
    const latestAssistant = [...messages].reverse().find((message) => message.role === 'assistant');
    if (latestAssistant && liveRegionRef.current) {
      liveRegionRef.current.textContent = latestAssistant.streaming
        ? 'Assistant is formulating a response'
        : `Assistant response updated at ${new Date(latestAssistant.createdAt).toLocaleTimeString()}`;
    }
  }, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) return;
    await sendMessage(trimmed);
    setPrompt('');
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      void sendMessage(prompt.trim());
      setPrompt('');
    }
  };

  return (
    <div className="chat-view">
      <div className="chat-transcript" ref={listRef} role="log" aria-live="polite" aria-label="Conversation transcript">
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} onCitationSelect={setActiveCitation} />
        ))}
      </div>
      <div className="live-region sr-only" ref={liveRegionRef} aria-live="polite" aria-atomic="true" />
      <VoiceConsole />
      <form className="chat-form" onSubmit={handleSubmit} aria-label="Send a question to the assistant">
        <label htmlFor="prompt" className="sr-only">
          Ask a question
        </label>
        <textarea
          id="prompt"
          name="prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          required
          placeholder="Ask about compliance history, investigations, or policy timelines..."
        />
        <div className="chat-actions">
          <button type="submit" disabled={loading}>
            {loading ? 'Sending…' : 'Send'}
          </button>
          <button type="button" onClick={() => void retryLast()} disabled={loading}>
            Resend Last
          </button>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </form>
    </div>
  );
}

function ChatBubble({
  message,
  onCitationSelect,
}: {
  message: ChatMessage;
  onCitationSelect: (citation: Citation) => void;
}): JSX.Element {
  return (
    <article
      className={`chat-bubble chat-bubble-${message.role}${message.error ? ' chat-bubble-error' : ''}`}
      aria-live={message.streaming ? 'polite' : 'off'}
    >
      <header>
        <span className="chat-role" aria-label={message.role === 'user' ? 'User message' : 'Assistant message'}>
          {message.role === 'user' ? 'You' : 'Assistant'}
        </span>
        <time dateTime={message.createdAt}>{new Date(message.createdAt).toLocaleTimeString()}</time>
      </header>
      {message.content ? (
        <ReactMarkdown
          className="chat-markdown"
          remarkPlugins={[remarkGfm]}
          components={markdownComponents}
          skipHtml
        >
          {message.content}
        </ReactMarkdown>
      ) : (
        message.streaming && <p className="chat-streaming">Streaming response…</p>
      )}
      {message.error && (
        <p role="alert" className="error">
          {message.error}
        </p>
      )}
      {message.citations.length > 0 && (
        <ul className="citation-list">
          {message.citations.map((citation: Citation) => (
            <li key={citation.docId}>
              <button
                type="button"
                onClick={() => onCitationSelect(citation)}
                className="citation-link"
              >
                {citation.title ?? citation.docId}
              </button>
              {citation.uri && (
                <a href={citation.uri} target="_blank" rel="noopener noreferrer" className="citation-external">
                  Open source
                </a>
              )}
              {citation.confidence !== undefined && citation.confidence !== null && (
                <span className="confidence">Confidence {(citation.confidence * 100).toFixed(0)}%</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
