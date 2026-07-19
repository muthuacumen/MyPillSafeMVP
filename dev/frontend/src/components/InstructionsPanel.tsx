import { useState } from 'react';
import { Loader2, Languages } from 'lucide-react';
import { instructionsApi } from '@/api/instructions';
import type { Prescription } from '@/types';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'ar', label: 'العربية' },
  { code: 'es', label: 'Español' },
] as const;

interface Props {
  prescription: Prescription;
}

export default function InstructionsPanel({ prescription }: Props) {
  const [lang, setLang] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInstructions = async (nextLang: string) => {
    setLang(nextLang);
    setLoading(true);
    setError(null);
    try {
      const { data } = await instructionsApi.getMessage({
        drug_name: prescription.drug_name,
        dosage: prescription.dosage,
        frequency_type: prescription.frequency_type ?? 'UNKNOWN',
        specific_times: prescription.specific_times,
        with_food: prescription.with_food,
        purpose: prescription.purpose,
        max_daily_dose: prescription.max_daily_dose,
        language: nextLang,
      });
      setMessage(data.message);
    } catch {
      setError('Could not load instructions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-3 border-t border-slate-100">
      <div className="flex items-center gap-1.5 mb-2">
        <Languages className="h-3.5 w-3.5 text-slate-400" />
        <span className="text-xs font-medium text-slate-500">Read my instructions</span>
      </div>
      <div className="flex gap-1 mb-2 flex-wrap">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            onClick={() => fetchInstructions(l.code)}
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
      {loading && <Loader2 className="h-5 w-5 text-teal-600 animate-spin" />}
      {error && <p className="text-sm text-danger-text">{error}</p>}
      {message && !loading && (
        <p
          dir={lang === 'ar' ? 'rtl' : 'ltr'}
          className="text-xl font-semibold text-slate-900 leading-relaxed mt-1 p-3 bg-teal-50 rounded-xl border border-teal-100"
        >
          {message}
        </p>
      )}
    </div>
  );
}
