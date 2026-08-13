import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Mail, Calendar, CheckCircle2, UserRound, ArrowLeft, MailCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Input } from '@/components/ui/Input';
import { PasswordField } from '@/components/ui/PasswordField';
import { PasswordStrengthMeter } from '@/components/ui/PasswordStrengthMeter';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { Logo } from '@/components/ui/Logo';
import { useAuth } from '@/hooks/useAuth';

const schema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  email: z.string().email('Enter a valid email'),
  date_of_birth: z.string().min(1, 'Date of birth is required'),
  password: z
    .string()
    .min(8, 'Minimum 8 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/\d/, 'Must contain a number'),
  preferred_language: z.string().default('en'),
});
type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const { t } = useTranslation();
  const [serverError, setServerError] = useState('');
  // Registration is admin-gated (backend returns 202 and no tokens), so the
  // success path is NOT "go to the dashboard" -- there is no session to go
  // to. Swap the form for a waiting state instead.
  const [pendingApproval, setPendingApproval] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: 'onBlur', reValidateMode: 'onChange' });

  const password = watch('password', '');

  const onSubmit = async (data: FormData) => {
    setServerError('');
    try {
      if ((await registerUser(data)) === 'pending_approval') {
        setPendingApproval(true);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { error?: { message?: string } } } } })
        ?.response?.data?.detail?.error?.message;
      setServerError(msg ?? 'Registration failed. Please try again.');
    }
  };

  // Copy (including the displayed value, which differs in French -- "1 in 4"
  // vs "1 sur 4") lives in `auth.stats.*`.
  const stats = ['stat1', 'stat2', 'stat3', 'stat4'];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-2/5 relative overflow-hidden bg-brand-hero">
        <div className="absolute -top-20 -right-20 h-80 w-80 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute bottom-0 left-0 h-96 w-96 rounded-full bg-white/8 blur-3xl" />

        <div className="relative z-10 flex flex-col justify-between p-10 w-full">
          <Link to="/" className="inline-flex w-fit focus-visible:ring" aria-label={t('auth.backHome')}>
            <Logo onDark className="h-9" />
          </Link>

          <div className="space-y-5">
            <h1 className="text-3xl font-extrabold text-white leading-tight tracking-tight">
              {t('auth.registerHeroTitle')}
            </h1>

            <div className="grid grid-cols-2 gap-4">
              {stats.map((key) => (
                <div key={key} className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-4">
                  <p className="text-2xl font-extrabold text-white">{t(`auth.stats.${key}.value`)}</p>
                  <p className="text-xs text-teal-100/70 mt-1">{t(`auth.stats.${key}.label`)}</p>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-teal-100/60">
              <span>{t('auth.badge')}</span>
              <span>·</span>
              <span>{t('auth.decisionSupportOnly')}</span>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-6 w-6 rounded-full bg-white/20 flex items-center justify-center">
                <CheckCircle2 className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="text-sm font-medium text-white">{t('auth.abstainTitle')}</span>
            </div>
            <p className="text-xs text-teal-100/70">{t('auth.abstainBody')}</p>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 relative flex items-start justify-center px-6 py-10 overflow-y-auto auth-panel-bg">
        <div className="pointer-events-none absolute top-16 right-[6%] h-72 w-72 rounded-full bg-teal-100/50 blur-3xl" />
        <div className="pointer-events-none absolute bottom-10 left-[4%] h-64 w-64 rounded-full bg-teal-50/70 blur-3xl" />

        <div className="relative w-full max-w-lg animate-fade-in">
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

          {pendingApproval ? (
            <div
              role="status"
              aria-live="polite"
              className="card p-8 sm:p-10 shadow-lg shadow-slate-200/60 text-center"
            >
              <div className="mx-auto h-14 w-14 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center">
                <MailCheck className="h-7 w-7 text-teal-600" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 mt-5">
                {t('auth.register.pendingTitle')}
              </h2>
              <p className="text-slate-600 mt-3 text-sm leading-relaxed">
                {t('auth.register.pendingBody')}
              </p>
              <Link
                to="/login"
                className="mt-7 inline-flex items-center justify-center min-h-[44px] px-5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2"
              >
                {t('auth.register.pendingCta')}
              </Link>
            </div>
          ) : (
          <div className="card p-8 sm:p-10 shadow-lg shadow-slate-200/60">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900">{t('auth.register.title')}</h2>
              <p className="text-slate-500 mt-1.5 text-sm">{t('auth.register.subtitle')}</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {serverError && <Alert variant="error" message={serverError} />}

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label={t('auth.register.firstName')}
                  placeholder={t('auth.placeholders.firstName')}
                  autoFocus
                  icon={<UserRound className="h-4 w-4" />}
                  disabled={isSubmitting}
                  error={errors.first_name?.message}
                  {...register('first_name')}
                />
                <Input
                  label={t('auth.register.lastName')}
                  placeholder={t('auth.placeholders.lastName')}
                  disabled={isSubmitting}
                  error={errors.last_name?.message}
                  {...register('last_name')}
                />
              </div>

              <Input
                label={t('auth.register.email')}
                type="email"
                placeholder={t('auth.placeholders.email')}
                autoComplete="email"
                icon={<Mail className="h-4 w-4" />}
                disabled={isSubmitting}
                error={errors.email?.message}
                {...register('email')}
              />

              <Input
                label={t('auth.register.dob')}
                type="date"
                icon={<Calendar className="h-4 w-4" />}
                disabled={isSubmitting}
                error={errors.date_of_birth?.message}
                hint={t('auth.register.dobHint')}
                {...register('date_of_birth')}
              />

              <div>
                <PasswordField
                  label={t('auth.register.password')}
                  placeholder={t('auth.placeholders.newPassword')}
                  autoComplete="new-password"
                  disabled={isSubmitting}
                  error={errors.password?.message}
                  {...register('password')}
                />
                <PasswordStrengthMeter password={password} />
              </div>

              <Button type="submit" loading={isSubmitting} className="w-full" size="lg">
                {t('auth.register.submit')}
              </Button>
            </form>
          </div>
          )}

          {!pendingApproval && (
            <p className="mt-6 text-center text-sm text-slate-500">
              {t('auth.register.haveAccount')}{' '}
              <Link to="/login" className="text-teal-600 hover:text-teal-700 font-medium transition-colors">
                {t('auth.register.signIn')}
              </Link>
            </p>
          )}

          <p className="mt-6 text-center text-xs text-slate-400">
            {t('auth.register.disclaimer')}
          </p>
        </div>
      </div>
    </div>
  );
}
