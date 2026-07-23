import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageCircleQuestion, Mic, Send, X } from 'lucide-react';
import { assistantApi, type AssistantConversationTurn, type AssistantSource } from '@/api/assistant';
import { useAuthStore } from '@/store/authStore';

// ---------------------------------------------------------------------------
// Content pack §8 strings -- VERBATIM. Layout/styling is ours; words are not.
// ---------------------------------------------------------------------------

const GREETING_EN =
  "Hello! I'm the MyPillSafe Assistant. I can explain how MyPillSafe works — the pill " +
  "verification, the safety design, the research behind it, and the team. I can't answer " +
  'questions about your medications; the app has a dedicated, safeguarded Q&A for that. What ' +
  'would you like to know?';

const GREETING_FR =
  "Bonjour ! Je suis l'Assistant MyPillSafe. Je peux vous expliquer comment MyPillSafe " +
  'fonctionne — la vérification des comprimés, la conception axée sur la sécurité, la ' +
  "recherche et l'équipe. Je ne peux pas répondre aux questions sur vos médicaments ; " +
  "l'application dispose d'une section Q&R dédiée et sécurisée pour cela. Que voulez-vous " +
  'savoir ?';

const DISCLAIMER_EN =
  '⚠️ This assistant explains the MyPillSafe project only. It cannot answer questions about ' +
  'your medications — use "Ask about my medication" in the app, and always verify with a ' +
  'pharmacist.';

const DISCLAIMER_FR =
  "⚠️ Cet assistant explique uniquement le projet MyPillSafe. Il ne peut pas répondre aux " +
  'questions sur vos médicaments — utilisez « Poser une question sur mon médicament » dans ' +
  "l'application, et vérifiez toujours auprès d'un pharmacien.";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  confidence?: number;
  sources?: AssistantSource[];
  latency?: number;
  usedLlm?: boolean;
  language?: string;
  suggestedQuestions?: string[];
  clarificationNeeded?: boolean;
  clarificationOptions?: string[];
  redirectToQa?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Renders `**bold**` spans as <strong> -- the content pack's redirect
 * strings use markdown-style bold for feature names; this keeps the words
 * verbatim while giving them visual emphasis (styling is ours, words are
 * not). */
function renderWithBold(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

/** 0-100 raw fuzzy-match score (not 0-1) -- calibrated to the backend's
 * confidence zones (>=60 LLM path, 40-59 clarification, <40 fallback). */
function getConfBadge(score: number): { label: string; className: string } {
  if (score >= 70) return { label: 'High', className: 'bg-green-100 text-green-800' };
  if (score >= 60) return { label: 'Good', className: 'bg-blue-100 text-blue-800' };
  if (score >= 40) return { label: 'Moderate', className: 'bg-orange-100 text-orange-800' };
  return { label: 'Low', className: 'bg-red-100 text-red-800' };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AssistantWidget() {
  const { pathname } = useLocation();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const [isOpen, setIsOpen] = useState(false);
  const [lang, setLang] = useState<'en' | 'fr'>('en');
  const [messages, setMessages] = useState<Message[]>([{ id: 'initial-bot', role: 'bot', content: GREETING_EN }]);
  const [history, setHistory] = useState<AssistantConversationTurn[]>([]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputWasVoiceRef = useRef(false);

  // Never two chat UIs on one screen -- the Q&A page has its own dedicated,
  // safeguarded medication chat.
  const hideOnThisPage = pathname === '/dashboard/qa';

  useEffect(() => {
    const locale = typeof navigator !== 'undefined' ? navigator.language : 'en';
    if (locale.startsWith('fr')) {
      setLang('fr');
      setMessages([{ id: 'initial-bot', role: 'bot', content: GREETING_FR }]);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  const switchLang = (next: 'en' | 'fr') => {
    setLang(next);
    setHistory([]);
    setMessages((prev) =>
      prev.map((m) => (m.id === 'initial-bot' ? { ...m, content: next === 'fr' ? GREETING_FR : GREETING_EN } : m)),
    );
  };

  const speakText = (text: string, language: 'en' | 'fr') => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/\*\*/g, ''));
    utterance.lang = language === 'fr' ? 'fr-FR' : 'en-US';
    window.speechSynthesis.speak(utterance);
  };

  const toggleSources = (id: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', content: text }]);
    setInputText('');
    setIsLoading(true);

    const historySnapshot = history.slice(-10);

    try {
      const { data } = await assistantApi.chat({ query: text, language: lang, history: historySnapshot });
      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        content: data.response,
        confidence: data.confidence,
        sources: data.sources,
        latency: data.latency,
        usedLlm: data.used_llm,
        language: data.language,
        suggestedQuestions: data.suggested_questions ?? [],
        clarificationNeeded: data.clarification_needed ?? false,
        clarificationOptions: data.clarification_options ?? [],
        redirectToQa: data.redirect_to_qa ?? false,
      };
      setMessages((prev) => [...prev, botMsg]);
      setHistory((prev) => [...prev, { role: 'user', content: text }, { role: 'bot', content: data.response }]);

      if (inputWasVoiceRef.current) speakText(data.response, lang);
      inputWasVoiceRef.current = false;
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'bot',
          content: lang === 'fr' ? "Désolé, une erreur s'est produite. Veuillez réessayer." : 'Sorry, I encountered an error. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    if (typeof window === 'undefined' || !navigator.mediaDevices) {
      alert('Audio recording is not supported in this environment.');
      return;
    }
    try {
      window.speechSynthesis?.cancel();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      alert('Microphone access denied or unavailable. Ensure you are on HTTPS or localhost.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendAudioBlob = async (blob: Blob) => {
    setIsLoading(true);
    try {
      const { data } = await assistantApi.voice(blob, lang);
      if (data.text) {
        inputWasVoiceRef.current = true;
        void handleSendMessage(data.text);
      } else {
        setIsLoading(false);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `vox-err-${Date.now()}`,
          role: 'bot',
          content: lang === 'fr' ? "Impossible de transcrire l'audio." : 'Could not transcribe audio.',
        },
      ]);
      setIsLoading(false);
    }
  };

  if (hideOnThisPage) return null;

  return (
    // bottom-20 on mobile clears the dashboard's fixed BottomTabBar
    // (md:hidden, ~64px tall); md:bottom-6 matches its own breakpoint once
    // the tab bar is gone (desktop dashboard + all of PublicLayout, which
    // never has a bottom tab bar).
    <div className="fixed bottom-20 md:bottom-6 right-4 sm:right-6 z-40 font-sans">
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Open MyPillSafe Assistant"
          className="bg-navy text-white p-4 rounded-full shadow-lg hover:bg-teal-600 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 min-h-[44px] min-w-[44px]"
        >
          <MessageCircleQuestion className="w-6 h-6" />
        </button>
      )}

      {isOpen && (
        <div className="w-80 sm:w-96 h-[70vh] max-h-[580px] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden border border-slate-200">
          {/* Header */}
          <div className="bg-navy px-4 py-3 text-white flex items-center justify-between flex-shrink-0">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-sm leading-tight">MyPillSafe Assistant</h3>
                <span className="bg-coral text-white text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide">
                  No Medical Advice
                </span>
              </div>
              <p className="text-[10px] text-white/50 mt-0.5">
                {lang === 'fr' ? 'À propos de ce projet · Pas un outil médical' : 'About this project · Not a medication tool'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center rounded-full bg-white/15 p-0.5 text-[10px] font-bold leading-none">
                <button
                  type="button"
                  onClick={() => switchLang('en')}
                  aria-label="Switch to English"
                  className={`px-2.5 py-1 rounded-full transition-colors ${lang === 'en' ? 'bg-white text-navy' : 'text-white/70 hover:text-white'}`}
                >
                  EN
                </button>
                <button
                  type="button"
                  onClick={() => switchLang('fr')}
                  aria-label="Passer en français"
                  className={`px-2.5 py-1 rounded-full transition-colors ${lang === 'fr' ? 'bg-white text-navy' : 'text-white/70 hover:text-white'}`}
                >
                  FR
                </button>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                aria-label="Close chat"
                className="text-white/60 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Disclaimer strip */}
          <div className="bg-amber-50 border-b border-amber-200 px-3 py-1.5 text-[10px] text-amber-800 text-center flex-shrink-0 leading-snug">
            {lang === 'fr' ? DISCLAIMER_FR : DISCLAIMER_EN}
          </div>

          {/* Messages */}
          <div className="flex-1 p-3 overflow-y-auto bg-slate-50 flex flex-col gap-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col gap-1 max-w-[85%] ${msg.role === 'user' ? 'self-end ml-auto' : 'self-start'}`}>
                <div
                  className={`p-3 rounded-lg text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-navy text-white rounded-br-none shadow-md'
                      : 'bg-white text-slate-800 shadow-sm border border-slate-100 rounded-bl-none'
                  }`}
                >
                  {renderWithBold(msg.content)}
                </div>

                {msg.role === 'bot' && msg.redirectToQa && (
                  <Link
                    to={isAuthenticated ? '/dashboard/qa' : '/login'}
                    className="inline-flex items-center gap-1.5 self-start text-xs font-semibold px-3 py-2 rounded-full bg-teal-600 text-white hover:bg-teal-700 transition-colors min-h-[36px]"
                  >
                    <MessageCircleQuestion className="h-3.5 w-3.5" />
                    {lang === 'fr' ? 'Poser une question sur mon médicament' : 'Ask about my medication'}
                  </Link>
                )}

                {msg.role === 'bot' && msg.confidence !== undefined && !msg.redirectToQa && (
                  <div className="flex items-center gap-1.5 flex-wrap text-[10px]">
                    {(() => {
                      const { label, className } = getConfBadge(msg.confidence!);
                      return (
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full font-bold ${className}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                          {label} {msg.confidence!.toFixed(0)}%
                        </span>
                      );
                    })()}
                    {msg.language && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-semibold uppercase tracking-wide">
                        {msg.language}
                      </span>
                    )}
                    {msg.latency !== undefined && <span className="text-slate-400">{msg.latency}s</span>}
                    {msg.usedLlm === false && <span className="text-slate-400 italic">(fallback)</span>}
                    {msg.sources && msg.sources.length > 0 && (
                      <button
                        type="button"
                        onClick={() => toggleSources(msg.id)}
                        className="text-teal-700 font-semibold hover:underline ml-0.5"
                      >
                        {expandedSources.has(msg.id)
                          ? lang === 'fr'
                            ? 'Masquer les sources'
                            : 'Hide sources'
                          : lang === 'fr'
                            ? `Voir sources (${msg.sources.length})`
                            : `Show sources (${msg.sources.length})`}
                      </button>
                    )}
                  </div>
                )}

                {msg.role === 'bot' && msg.sources && expandedSources.has(msg.id) && (
                  <div className="bg-slate-100 rounded-lg p-2 text-[10px] text-slate-600 space-y-1.5">
                    {msg.sources.map((s, i) => (
                      <div key={i} className="border-b border-slate-200 last:border-0 pb-1.5 last:pb-0">
                        <span className="font-semibold text-navy capitalize">{s.category.replace(/_/g, ' ')}</span>
                        {' — '}
                        {s.question} <span className="text-slate-400">({s.score.toFixed(0)}%)</span>
                      </div>
                    ))}
                  </div>
                )}

                {msg.role === 'bot' && msg.clarificationNeeded && msg.clarificationOptions && msg.clarificationOptions.length > 0 && (
                  <div className="flex flex-col gap-1.5 mt-1">
                    {msg.clarificationOptions.map((opt, i) => (
                      <button
                        key={i}
                        type="button"
                        disabled={isLoading}
                        onClick={() => void handleSendMessage(opt)}
                        className="text-left text-[11px] px-3 py-1.5 rounded-full border border-teal-600 text-teal-700 hover:bg-teal-600 hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                {msg.role === 'bot' && !msg.clarificationNeeded && msg.suggestedQuestions && msg.suggestedQuestions.length > 0 && (
                  <div className="flex flex-col gap-1 mt-1">
                    <p className="text-[9px] text-slate-400 uppercase tracking-wide">
                      {lang === 'fr' ? 'Vous pourriez aussi demander' : 'You might also ask'}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {msg.suggestedQuestions.map((q, i) => (
                        <button
                          key={i}
                          type="button"
                          disabled={isLoading}
                          onClick={() => void handleSendMessage(q)}
                          className="text-[10px] px-2 py-1 rounded-full bg-slate-100 text-slate-500 hover:bg-navy hover:text-white transition-colors text-left disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="self-start bg-white shadow-sm border border-slate-100 p-3 rounded-lg rounded-bl-none text-sm max-w-[80%]">
                <span className="flex items-center gap-1.5 text-slate-500">
                  <span className="w-1.5 h-1.5 bg-teal-600 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-teal-600 rounded-full animate-bounce [animation-delay:75ms]" />
                  <span className="w-1.5 h-1.5 bg-teal-600 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="ml-1">{lang === 'fr' ? 'Réflexion…' : 'Thinking…'}</span>
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input row */}
          <div className="p-3 bg-white border-t border-slate-200 flex items-center gap-2 flex-shrink-0">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleSendMessage(inputText);
              }}
              placeholder={lang === 'fr' ? 'Votre message…' : 'Type a message…'}
              disabled={isLoading}
              className="flex-1 border border-slate-200 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 disabled:opacity-50"
            />

            <button
              type="button"
              onMouseDown={() => void startRecording()}
              onMouseUp={stopRecording}
              onMouseLeave={stopRecording}
              onTouchStart={(e) => {
                e.preventDefault();
                void startRecording();
              }}
              onTouchEnd={(e) => {
                e.preventDefault();
                stopRecording();
              }}
              disabled={isLoading}
              aria-label={lang === 'fr' ? 'Maintenir pour enregistrer' : 'Hold to record voice'}
              className={`p-2 rounded-full text-white transition-all focus:outline-none flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center ${
                isRecording ? 'bg-coral scale-110 shadow-lg' : 'bg-teal-600 hover:bg-navy'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <Mic className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => void handleSendMessage(inputText)}
              disabled={isLoading || !inputText.trim()}
              aria-label={lang === 'fr' ? 'Envoyer' : 'Send message'}
              className="bg-teal-600 text-white p-2 rounded-full hover:bg-navy transition-colors focus:outline-none flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
