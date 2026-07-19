import { AlertCircle, CheckCircle2, Info, XCircle } from 'lucide-react';

type AlertVariant = 'success' | 'error' | 'warning' | 'info';

const styles: Record<AlertVariant, { wrapper: string; icon: React.ReactNode }> = {
  success: {
    wrapper: 'bg-success-bg border border-success-border text-success-text',
    icon: <CheckCircle2 className="h-5 w-5 text-success-text shrink-0 mt-0.5" />,
  },
  error: {
    wrapper: 'bg-danger-bg border border-danger-border text-danger-text',
    icon: <XCircle className="h-5 w-5 text-danger-text shrink-0 mt-0.5" />,
  },
  warning: {
    wrapper: 'bg-warning-bg border border-warning-border text-warning-text',
    icon: <AlertCircle className="h-5 w-5 text-warning-text shrink-0 mt-0.5" />,
  },
  info: {
    wrapper: 'bg-blue-50 border border-blue-200 text-blue-800',
    icon: <Info className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />,
  },
};

interface AlertProps {
  variant?: AlertVariant;
  message: string;
  className?: string;
}

export function Alert({ variant = 'info', message, className = '' }: AlertProps) {
  const { wrapper, icon } = styles[variant];
  return (
    <div role="alert" aria-live="polite" className={`flex items-start gap-3 rounded-xl p-4 text-sm ${wrapper} ${className}`}>
      {icon}
      <span>{message}</span>
    </div>
  );
}
