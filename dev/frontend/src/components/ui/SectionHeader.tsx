import type { ReactNode } from 'react';

interface SectionHeaderProps {
  children: ReactNode;
  action?: ReactNode;
}

export function SectionHeader({ children, action }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{children}</h2>
      {action}
    </div>
  );
}
