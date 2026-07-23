import { NavLink } from 'react-router-dom';
import { FileText, LayoutDashboard, MessageCircleQuestion, Pill, ScanLine } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// Mobile-only bottom tab bar (Phase 5 §E) -- replaces the desktop Sidebar
// under `md:`. Five primary destinations only; everything else (profile,
// education, settings, scan history) stays reachable from the Navbar's
// "Menu" dropdown and/or a Dashboard quick-action tile (Phase 6: Scan
// History left the tab bar to make room for the split Scan Rx / Scan Pill
// tabs -- see router/index.tsx + DashboardPage.tsx).
const TABS = [
  { to: '/dashboard', labelKey: 'nav.short.dashboard', icon: LayoutDashboard, end: true },
  { to: '/dashboard/scan-prescription', labelKey: 'nav.short.scanRx', icon: FileText, end: false },
  { to: '/dashboard/scan-pill', labelKey: 'nav.short.scanPill', icon: ScanLine, end: false },
  { to: '/dashboard/medications', labelKey: 'nav.short.medications', icon: Pill, end: false },
  { to: '/dashboard/qa', labelKey: 'nav.short.qa', icon: MessageCircleQuestion, end: false },
];

// Phase 6 audit (PisaPillsafeFindings.md §2/§7): app chrome (this bar + the
// Navbar) carries the navy brand anchor; content surfaces (page backgrounds,
// cards) stay neutral slate by design -- see the matching note in
// tailwind.config.ts next to the brand tokens.
export default function BottomTabBar() {
  const { t } = useTranslation();

  return (
    <nav
      aria-label="Primary"
      className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-navy border-t border-white/10 grid grid-cols-5"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {TABS.map(({ to, labelKey, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] text-[10px] font-medium transition-colors focus-visible:outline-none ${
              isActive ? 'text-white' : 'text-white/70 hover:text-white'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={`h-5 w-5 ${isActive ? 'text-teal-300' : ''}`} strokeWidth={1.8} />
              {t(labelKey)}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
