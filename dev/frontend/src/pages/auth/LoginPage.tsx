import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ShieldCheck, Mail, ScanLine, Activity, Lock, ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Input } from '@/components/ui/Input';
import { PasswordField } from '@/components/ui/PasswordField';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { Logo } from '@/components/ui/Logo';
import { useAuth } from '@/hooks/useAuth';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const { t } = useTranslation();
  const [serverError, setServerError] = useState('');
  const [pendingApproval, setPendingApproval] = useState(false);
  const [showForgotNote, setShowForgotNote] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: 'onBlur', reValidateMode: 'onChange' });

  const onSubmit = async (data: FormData) => {
    setServerError('');
    setPendingApproval(false);
    try {
      await login(data);
    } catch (err: unknown) {
      const error = (
        err as { response?: { data?: { detail?: { error?: { code?: string; message?: string } } } } }
      )?.response?.data?.detail?.error;
      // A pending account is NOT a failed sign-in — the password was right.
      // Rendering it as a red "invalid credentials" error would send people
      // off resetting a password that works fine.
      if (error?.code === 'ACCOUNT_PENDING_APPROVAL') {
        setPendingApproval(true);
        return;
      }
      setServerError(error?.message ?? 'Login failed. Please try again.');
    }
  };

  // Copy lives in `auth.features.*`; only the icon and the key stay here.
  const features = [
    { icon: ScanLine, key: 'feature1' },
    { icon: Activity, key: 'feature2' },
    { icon: ShieldCheck, key: 'feature3' },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-brand-hero">
        <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute -bottom-40 -left-20 h-[500px] w-[500px] rounded-full bg-white/8 blur-3xl" />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <Link to="/" className="inline-flex w-fit focus-visible:ring" aria-label={t('auth.backHome')}>
            <Logo onDark className="h-9" />
          </Link>

          <div className="space-y-6">
            <div>
              <h1 className="text-4xl font-extrabold text-white leading-tight tracking-tight">
                {t('auth.brand.tagline')}
              </h1>
              <p className="mt-4 text-teal-50/80 leading-relaxed max-w-md">
                {t('auth.brand.description')}
              </p>
            </div>

            <div className="space-y-4">
              {features.map(({ icon: Icon, key }) => (
                <div key={key} className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-xl bg-white/15 border border-white/25 flex items-center justify-center shrink-0">
                    <Icon className="h-5 w-5 text-white" strokeWidth={1.8} />
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{t(`auth.features.${key}.title`)}</p>
                    <p className="text-teal-100/70 text-xs mt-0.5">{t(`auth.features.${key}.desc`)}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-teal-100/60">
              <span>{t('auth.badge')}</span>
              <span>·</span>
              <span>{t('auth.decisionSupportOnly')}</span>
              <span>·</span>
              <span>{t('auth.alwaysConfirm')}</span>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-4">
            <p className="text-sm text-white/90 italic">{t('auth.brand.principle')}</p>
            <p className="text-xs text-teal-200 mt-2">{t('auth.brand.principleNote')}</p>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 relative flex items-center justify-center px-6 py-12 overflow-y-auto auth-panel-bg">
        <div className="pointer-events-none absolute top-16 right-[8%] h-72 w-72 rounded-full bg-teal-100/50 blur-3xl" />
        <div className="pointer-events-none absolute bottom-10 left-[6%] h-64 w-64 rounded-full bg-teal-50/70 blur-3xl" />

        <div className="relative w-full max-w-md animate-fade-in">
          {/* Mobile logo */}
          <div className="flex items-center mb-8 lg:hidden">
            <Link to="/" aria-label={t('auth.backHome')}>
              <Logo className="h-9" />
            </Link>
          </div>

          {/* Back to home + language switcher */}
          <div className="flex items-center justify-between mb-6">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" /> {t('auth.backHome')}
            </Link>
            <LanguageSwitcher />
          </div>

          <div className="card p-8 sm:p-10 shadow-lg shadow-slate-200/60">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900">{t('auth.login.title')}</h2>
              <p className="text-slate-500 mt-1.5 text-sm">{t('auth.login.subtitle')}</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {serverError && <Alert variant="error" message={serverError} />}
              {/* Informational, not an error: the credentials were accepted,
                  the account just isn't approved yet. */}
              {pendingApproval && <Alert variant="info" message={t('auth.login.pendingApproval')} />}

              <Input
                label={t('auth.login.email')}
                type="email"
                placeholder={t('auth.placeholders.email')}
                autoComplete="email"
                autoFocus
                icon={<Mail className="h-4 w-4" />}
                disabled={isSubmitting}
                error={errors.email?.message}
                {...register('email')}
              />

              <PasswordField
                label={t('auth.login.password')}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={isSubmitting}
                error={errors.password?.message}
                {...register('password')}
              />

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setShowForgotNote(true)}
                  className="text-xs text-teal-600 hover:text-teal-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 rounded"
                >
                  {t('auth.login.forgotPassword')}
                </button>
              </div>
              {showForgotNote && (
                <p role="status" className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-3 -mt-2">
                  {t('auth.login.forgotPasswordNote')}
                </p>
              )}

              <Button type="submit" loading={isSubmitting} className="w-full" size="lg">
                <Lock className="h-4 w-4" />
                {t('auth.login.submit')}
              </Button>
            </form>
          </div>

          <p className="mt-6 text-center text-sm text-slate-500">
            {t('auth.login.noAccount')}{' '}
            <Link to="/register" className="text-teal-600 hover:text-teal-700 font-medium transition-colors">
              {t('auth.login.createFree')}
            </Link>
          </p>

          <p className="mt-6 text-center text-xs text-slate-400">
            {t('auth.login.disclaimer')}
          </p>
        </div>
      </div>
    </div>
  );
}
