import { useEffect, useState } from 'react';
import { Bell, Search, Volume2, VolumeX } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { voice } from '@/lib/voiceAssistant';

interface TopbarProps {
  titleKey?: string;
}

export default function Topbar({ titleKey }: TopbarProps) {
  const user = useAuthStore((s) => s.user);
  const { t } = useTranslation();
  const [voiceEnabled, setVoiceEnabled] = useState(false);

  useEffect(() => {
    setVoiceEnabled(voice.isEnabled());
    return voice.subscribe(setVoiceEnabled);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
      {titleKey ? (
        <h1 className="text-lg font-semibold text-slate-900">{t(titleKey)}</h1>
      ) : (
        <div />
      )}

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-400">
          <Search className="h-4 w-4" />
          <span className="text-xs">{t('search.placeholder')}</span>
          <kbd className="hidden md:block text-xs bg-white border border-slate-200 px-1.5 py-0.5 rounded font-mono text-slate-500">⌘K</kbd>
        </div>

        <LanguageSwitcher />

        <button
          type="button"
          onClick={() => voice.toggle()}
          aria-label={voiceEnabled ? 'Voice Assistant On' : 'Voice Assistant Off'}
          title="Voice Assistant On/Off"
          className={`relative h-11 w-11 rounded-xl border flex items-center justify-center transition-colors ${
            voiceEnabled
              ? 'bg-teal-50 border-teal-300 text-teal-600'
              : 'bg-white border-slate-200 text-slate-400 hover:text-slate-700 hover:border-teal-300'
          }`}
        >
          {voiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
        </button>

        <button aria-label="Notifications" className="relative h-11 w-11 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-400 hover:text-slate-700 hover:border-teal-300 transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute top-2.5 right-2.5 h-2 w-2 rounded-full bg-teal-500" />
        </button>

        <div className="h-11 w-11 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center">
          <span className="text-teal-700 text-sm font-bold">
            {user?.first_name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?'}
          </span>
        </div>
      </div>
    </header>
  );
}
