import client from './client';

export interface AssistantConversationTurn {
  role: 'user' | 'bot';
  content: string;
}

export interface AssistantSource {
  question: string;
  category: string;
  score: number;
}

export interface AssistantChatResponse {
  response: string;
  language: string;
  confidence: number;
  sources: AssistantSource[];
  latency: number;
  used_llm: boolean;
  suggested_questions: string[];
  clarification_needed: boolean;
  clarification_options: string[];
  redirect_to_qa: boolean;
}

export interface AssistantChatParams {
  query: string;
  language?: 'en' | 'fr';
  history?: AssistantConversationTurn[];
}

/** `/api/v1/assistant/*` -- the public, no-auth MyPillSafe Assistant
 * (project explainer widget). Distinct from `qaApi` (`/api/v1/qa/chat`),
 * which is the authenticated, DIN-scoped medication Q&A. */
export const assistantApi = {
  chat: (params: AssistantChatParams) =>
    client.post<AssistantChatResponse>('/assistant/chat', params, { timeout: 30_000 }),
  voice: (blob: Blob, language: 'en' | 'fr') => {
    const form = new FormData();
    form.append('audio', blob, 'voice.webm');
    form.append('language', language);
    return client.post<{ text: string }>('/assistant/voice', form, { timeout: 30_000 });
  },
};
