import { useTranslation } from 'react-i18next';
import { AlertTriangle, RotateCw } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ message, onRetry, className = '' }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div role="alert" className={`text-center py-10 px-4 ${className}`}>
      <div className="h-14 w-14 rounded-2xl bg-danger-bg border border-danger-border flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="h-7 w-7 text-danger-text" strokeWidth={1.8} />
      </div>
      <p className="font-semibold text-slate-900">{t('errorState.title')}</p>
      <p className="text-sm text-slate-500 mt-1.5 max-w-sm mx-auto">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="btn-secondary mt-5 min-h-[44px]"
        >
          <RotateCw className="h-4 w-4" /> {t('errorState.retry')}
        </button>
      )}
    </div>
  );
}
