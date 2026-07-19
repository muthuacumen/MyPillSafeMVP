interface LoadingSkeletonProps {
  variant?: 'stats' | 'card' | 'list' | 'page';
  rows?: number;
  className?: string;
}

/** CSS-only shimmer (Tailwind's built-in `animate-pulse`) — no extra dependency or config needed. */
export function LoadingSkeleton({ variant = 'card', rows = 3, className = '' }: LoadingSkeletonProps) {
  if (variant === 'page') {
    return (
      <div className={`flex items-center justify-center py-24 ${className}`} aria-busy="true" aria-live="polite">
        <div className="h-10 w-10 rounded-full border-4 border-teal-200 border-t-teal-600 animate-spin" />
      </div>
    );
  }

  if (variant === 'stats') {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`} aria-busy="true" aria-live="polite">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-5 flex items-center gap-4 animate-pulse">
            <div className="h-11 w-11 rounded-xl bg-slate-200 shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-2.5 w-16 rounded bg-slate-200" />
              <div className="h-4 w-10 rounded bg-slate-200" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className={`space-y-3 ${className}`} aria-busy="true" aria-live="polite">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-14 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className={`card p-5 space-y-3 animate-pulse ${className}`} aria-busy="true" aria-live="polite">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3 rounded bg-slate-200" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}
