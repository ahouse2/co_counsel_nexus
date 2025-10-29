import { del, get, set } from 'idb-keyval';
import { ChatMessage, TimelineEvent } from '@/types';

const CHAT_KEY = 'cocounsel-chat-history';
const TIMELINE_KEY = 'cocounsel-timeline-cache';
const CACHE_VERSION = '1.0.0';

interface VersionedPayload<T> {
  version: string;
  payload: T;
}

async function loadVersioned<T>(key: string): Promise<T | null> {
  const record = (await get<VersionedPayload<T>>(key)) || null;
  if (!record) return null;
  if (record.version !== CACHE_VERSION) {
    await del(key);
    return null;
  }
  return record.payload;
}

export async function saveChatHistory(messages: ChatMessage[]): Promise<void> {
  await set(CHAT_KEY, { version: CACHE_VERSION, payload: messages });
}

export async function loadChatHistory(): Promise<ChatMessage[]> {
  return (await loadVersioned<ChatMessage[]>(CHAT_KEY)) || [];
}

export async function saveTimeline(events: TimelineEvent[]): Promise<void> {
  await set(TIMELINE_KEY, { version: CACHE_VERSION, payload: events });
}

export async function loadTimeline(): Promise<TimelineEvent[]> {
  return (await loadVersioned<TimelineEvent[]>(TIMELINE_KEY)) || [];
}
