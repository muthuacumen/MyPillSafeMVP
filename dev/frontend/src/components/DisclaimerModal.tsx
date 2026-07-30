import { useTranslation } from 'react-i18next';
import { ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface DisclaimerModalProps {
  open: boolean;
  onAccept: () => void;
}

/** Cannot be dismissed by clicking outside — only the "I Understand" button closes it (Priority 5). */
export function DisclaimerModal({ open, onAccept }: DisclaimerModalProps) {
  const { t } = useTranslation();
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="disclaimer-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4"
    >
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 animate-slide-up">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-xl bg-warning-bg border border-warning-border flex items-center justify-center shrink-0">
            <ShieldAlert className="h-5 w-5 text-warning-text" />
          </div>
          <div>
            <h2 id="disclaimer-title" className="font-semibold text-slate-900 text-lg">
              {t('disclaimerModal.title')}
            </h2>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              {t('disclaimerModal.body')}
            </p>
          </div>
        </div>
        <Button onClick={onAccept} className="w-full mt-6" size="lg">
          {t('disclaimerModal.accept')}
        </Button>
      </div>
    </div>
  );
}
