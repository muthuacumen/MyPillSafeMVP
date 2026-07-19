import { useState } from 'react';
import { Volume2, VolumeX, Loader2 } from 'lucide-react';
import { remindersApi } from '@/api/reminders';

interface Props {
  medicationName: string;
  patientFirstName: string;
  initialLanguage?: string;
}

const LANGUAGES = [
  { code: 'en', label: 'English', speechLang: 'en-CA' },
  { code: 'fr', label: 'Français', speechLang: 'fr-CA' },
  { code: 'ar', label: 'العربية', speechLang: 'ar-SA' },
  { code: 'es', label: 'Español', speechLang: 'es-ES' },
] as const;

export default function ReminderAudio({ medicationName, patientFirstName, initialLanguage = 'en' }: Props) {
  const [lang, setLang] = useState(initialLanguage);
  const [loading, setLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = LANGUAGES.find((l) => l.code === lang) ?? LANGUAGES[0];

  const handleSpeak = async () => {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const { data } = await remindersApi.getMessage({
        medication_name: medicationName,
        patient_first_name: patientFirstName,
        language: lang,
      });
      setLoading(false);

      const utterance = new SpeechSynthesisUtterance(data.message);
      utterance.lang = selected.speechLang;
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => {
        setSpeaking(false);
        setError('Audio failed — check browser permissions.');
      };

      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    } catch {
      setLoading(false);
      setError('Could not generate reminder. Please try again.');
    }
  };

  return (
    <div className="pt-3 border-t border-slate-100">
      <div className="flex gap-1 mb-2 flex-wrap">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            onClick={() => {
              setLang(l.code);
              window.speechSynthesis.cancel();
              setSpeaking(false);
              setError(null);
            }}
            className={`px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${
              lang === l.code
                ? 'bg-teal-600 text-white'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700'
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={handleSpeak}
        disabled={loading}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
          speaking
            ? 'bg-danger-bg text-danger-text border border-danger-border hover:bg-red-100'
            : 'bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100'
        }`}
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : speaking ? (
          <VolumeX className="h-3.5 w-3.5" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" />
        )}
        {loading ? 'Generating…' : speaking ? 'Stop' : 'Hear Reminder'}
      </button>

      {error && <p className="text-xs text-danger-text mt-1">{error}</p>}
    </div>
  );
}
