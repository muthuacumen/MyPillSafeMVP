const RULES = [
  { test: (p: string) => p.length >= 8, label: '8+ characters' },
  { test: (p: string) => /[A-Z]/.test(p), label: 'Uppercase letter' },
  { test: (p: string) => /\d/.test(p), label: 'Number' },
];

export function PasswordStrengthMeter({ password }: { password: string }) {
  const passed = RULES.filter(({ test }) => test(password)).length;
  const strength =
    password.length === 0
      ? null
      : passed <= 1
        ? { label: 'Weak', bar: 'bg-red-400', text: 'text-red-500' }
        : passed === 2
          ? { label: 'Fair', bar: 'bg-amber-400', text: 'text-amber-600' }
          : { label: 'Strong', bar: 'bg-teal-500', text: 'text-teal-600' };

  return (
    <div className="mt-2.5">
      <div className="flex gap-1.5">
        {RULES.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              i < passed ? strength?.bar : 'bg-slate-200'
            }`}
          />
        ))}
      </div>
      <div className="flex items-center justify-between mt-2 gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {RULES.map(({ test, label }) => (
            <span
              key={label}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                test(password)
                  ? 'bg-teal-50 border-teal-300 text-teal-700'
                  : 'bg-slate-50 border-slate-200 text-slate-400'
              }`}
            >
              {label}
            </span>
          ))}
        </div>
        {strength && <span className={`text-xs font-semibold shrink-0 ${strength.text}`}>{strength.label}</span>}
      </div>
    </div>
  );
}
