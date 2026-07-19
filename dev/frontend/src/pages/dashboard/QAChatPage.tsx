import { useCallback, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  Cloud,
  HardDrive,
  Info,
  ListChecks,
  Loader2,
  MessageCircleQuestion,
  Send,
  ShieldAlert,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Input } from '@/components/ui/Input';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import { qaApi } from '@/api/qa';
import type { QAChatResponse } from '@/types';

const STANDARD_DISCLAIMER = 'Decision-support only — not medical advice. Verify with a pharmacist.';

const LANGUAGES = [
  { code: 'English', label: 'English' },
  { code: 'French', label: 'Français' },
  { code: 'Spanish', label: 'Español' },
  { code: 'Arabic', label: 'العربية' },
  { code: 'Tamil', label: 'தமிழ்' },
];

interface Turn {
  id: string;
  question: string;
  loading: boolean;
  error?: string;
  response?: QAChatResponse;
}

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Pulls the DIN out of a BB3 source/citation tag, e.g. "[DIN:2242680]" -> "2242680". */
function dinFromTag(tag: string): string | null {
  const match = /^\[DIN:(\d+)\]$/.exec(tag);
  return match ? match[1] : null;
}

function VoiceBadge({ voice: v, model }: { voice: QAChatResponse['voice']; model?: string }) {
  if (v === 'cb4') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded-full px-2 py-0.5">
        <Cloud className="h-3 w-3" /> {model ?? 'CB4'}
      </span>
    );
  }
  if (v === 'local_7b') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 border border-slate-200 rounded-full px-2 py-0.5">
        <HardDrive className="h-3 w-3" /> Offline fallback (local model)
      </span>
    );
  }
  return null;
}

function SourceChips({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {tags.map((tag) => {
        const din = dinFromTag(tag);
        return (
          <span key={tag} className="badge bg-slate-100 text-slate-600 border border-slate-200 text-[11px]">
            {din ? `DIN ${din}` : tag}
          </span>
        );
      })}
    </div>
  );
}

function TierDisclaimer({ text }: { text?: string }) {
  if (!text) return null;
  return <p className="text-xs text-slate-500 mt-2 italic">{text}</p>;
}

interface TurnCardProps {
  turn: Turn;
  onConfirm: (candidateName: string, originalQuestion: string) => void;
  onDeclineConfirm: () => void;
}

function TurnCard({ turn, onConfirm, onDeclineConfirm }: TurnCardProps) {
  const r = turn.response;

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-teal-600 text-white px-4 py-2.5 text-sm">
          {turn.question}
        </div>
      </div>

      {turn.loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500 px-1">
          <Loader2 className="h-4 w-4 animate-spin" /> Thinking this through — this can take a few seconds…
        </div>
      )}

      {turn.error && <Alert variant="error" message={turn.error} />}

      {r && r.status === 'confirm' && (
        <Card className="max-w-[90%]">
          <p className="text-sm text-slate-800">{r.answer}</p>
          <div className="flex gap-2 mt-3">
            <Button size="sm" onClick={() => onConfirm(r.resolution?.candidates?.[0]?.name ?? '', turn.question)}>
              Yes, I meant {r.resolution?.candidates?.[0]?.name}
            </Button>
            <Button size="sm" variant="secondary" onClick={onDeclineConfirm}>
              No
            </Button>
          </div>
        </Card>
      )}

      {r && r.status === 'pick_list' && (
        <Card className="max-w-[90%]">
          <p className="text-sm text-slate-800 mb-3">{r.answer}</p>
          <div className="flex flex-wrap gap-2">
            {r.resolution?.candidates?.map((c) => (
              <Button key={c.name} size="sm" variant="secondary" onClick={() => onConfirm(c.name, turn.question)}>
                {c.name}
              </Button>
            ))}
          </div>
        </Card>
      )}

      {r && (r.status === 'not_found' || r.status === 'no_entity') && (
        <div className="max-w-[90%] flex items-start gap-2.5 rounded-2xl rounded-bl-sm bg-slate-100 border border-slate-200 px-4 py-3 text-sm text-slate-700">
          <Info className="h-4 w-4 shrink-0 mt-0.5 text-slate-400" />
          <span>{r.answer}</span>
        </div>
      )}

      {r && r.status === 'refused_dosing' && (
        <Card className="max-w-[90%] border-warning-border bg-warning-bg">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-warning-text" />
            <p className="text-sm text-slate-800">{r.answer}</p>
          </div>
        </Card>
      )}

      {r && r.status === 'guard_refused' && (
        <div className="max-w-[90%] flex items-start gap-2.5 rounded-2xl rounded-bl-sm bg-danger-bg border border-danger-border px-4 py-3 text-sm text-danger-text">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{r.answer}</span>
        </div>
      )}

      {r && r.status === 'enumeration' && (
        <Card className="max-w-[95%]">
          <div className="flex items-center gap-2 mb-2">
            <ListChecks className="h-4 w-4 text-teal-600" />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Formulary list</span>
          </div>
          <pre className="whitespace-pre-wrap font-sans text-sm text-slate-800 leading-relaxed">{r.answer}</pre>
        </Card>
      )}

      {r && r.status === 'answered' && (
        <Card
          className={`max-w-[90%] ${r.abstained ? 'bg-slate-50' : ''}`}
          padding="sm"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-slate-800 whitespace-pre-wrap">{r.answer}</p>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <VoiceBadge voice={r.voice} model={r.model} />
          </div>
          <SourceChips tags={r.cited_tags && r.cited_tags.length > 0 ? r.cited_tags : []} />
          <TierDisclaimer text={r.disclaimer} />
        </Card>
      )}
    </div>
  );
}

export default function QAChatPage() {
  useVoicePageAnnounce('Ask about my medication');
  const [searchParams] = useSearchParams();
  const dinBypass = searchParams.get('din') || undefined;
  const dinBypassName = searchParams.get('name') || undefined;

  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [language, setLanguage] = useState('English');
  const inputRef = useRef<HTMLInputElement>(null);

  const send = useCallback(
    async (message: string, confirmedName?: string) => {
      const id = newId();
      setTurns((prev) => [...prev, { id, question: message, loading: true }]);
      try {
        const { data } = await qaApi.chat({
          message,
          din: dinBypass,
          confirmed_name: confirmedName,
          language,
        });
        setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, loading: false, response: data } : t)));
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { detail?: { error?: { message?: string } } } } })?.response?.data?.detail
            ?.error?.message ?? 'Something went wrong asking that question. Please try again.';
        setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, loading: false, error: message } : t)));
      }
    },
    [dinBypass, language],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    setInput('');
    void send(trimmed);
  };

  const handleConfirm = (candidateName: string, originalQuestion: string) => {
    if (!candidateName) return;
    void send(originalQuestion, candidateName);
  };

  const handleDeclineConfirm = () => {
    setTurns((prev) => [
      ...prev,
      {
        id: newId(),
        question: '(declined)',
        loading: false,
        response: {
          status: 'not_found',
          answer:
            "I couldn't find that medication in the Canadian formulary -- please check the spelling, give the ingredient name, or the DIN from the package.",
          voice: 'none',
        },
      },
    ]);
  };

  return (
    <div className="space-y-4 page-enter max-w-3xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <MessageCircleQuestion className="h-6 w-6 text-teal-600" />
            Ask about my medication
          </h1>
          {dinBypassName && (
            <p className="text-sm text-teal-700 mt-1">
              Asking about <span className="font-semibold">{dinBypassName}</span>
              {dinBypass ? ` (DIN ${dinBypass})` : ''}
            </p>
          )}
        </div>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          aria-label="Answer language"
          className="input-field !w-auto text-sm py-1.5"
        >
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {turns.length === 0 && (
          <Card className="text-center py-10">
            <MessageCircleQuestion className="h-10 w-10 text-teal-300 mx-auto mb-3" />
            <p className="font-semibold text-slate-900">Ask a question about a medication</p>
            <p className="text-sm text-slate-500 mt-1.5 max-w-sm mx-auto">
              For example: "what foods should I avoid with warfarin" or "can I take this with food".
              Name the medication, or pick one from your profile.
            </p>
          </Card>
        )}
        {turns.map((turn) => (
          <TurnCard key={turn.id} turn={turn} onConfirm={handleConfirm} onDeclineConfirm={handleDeclineConfirm} />
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 items-start pt-2 border-t border-slate-200">
        <div className="flex-1">
          <Input
            ref={inputRef}
            placeholder="Ask about a medication…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={!input.trim()}>
          <Send className="h-4 w-4" /> Ask
        </Button>
      </form>

      <p className="flex items-start gap-1.5 text-xs text-slate-400 pb-2">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        {STANDARD_DISCLAIMER}
      </p>
    </div>
  );
}
