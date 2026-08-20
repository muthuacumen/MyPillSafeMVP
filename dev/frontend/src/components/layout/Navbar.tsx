import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  BookOpen,
  ChevronDown,
  FileText,
  Grid3x3,
  LayoutDashboard,
  LogOut,
  Menu as MenuIcon,
  MessageCircleQuestion,
  Pill,
  ScanLine,
  Server,
  Settings,
  Shield,
  ShieldCheck,
  User,
  Users,
  Volume2,
  VolumeX,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { useAuth } from '@/hooks/useAuth';
import { Logo } from '@/components/ui/Logo';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { ABOUT_PAGES } from '@/components/AboutNav';
import { voice } from '@/lib/voiceAssistant';
import { isTrayCheckEnabled } from '@/lib/featureFlags';

interface MenuItem {
  to: string;
  labelKey: string;
  icon: LucideIcon;
  end?: boolean;
  /** Build-time gate, evaluated on every render (never at module load, so the
   * flag reflects the environment the app is actually running in). Absent =
   * always shown. */
  enabled?: () => boolean;
}

// Every authenticated destination in the app, in the order they appear in
// the "Menu" dropdown / mobile panel (Phase 6 -- replaces the desktop
// Sidebar entirely, see AppShell.tsx).
const MENU_ITEMS: MenuItem[] = [
  { to: '/dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, end: true },
  { to: '/dashboard/scan-prescription', labelKey: 'nav.scanRx', icon: FileText },
  { to: '/dashboard/scan-pill', labelKey: 'nav.scanPill', icon: ScanLine },
  // MPR1-T07: localhost tray-check page (6-slot grid) -- separate from the
  // Scan Pill single-pill flow above and from the marketing tray section on
  // PillVisionPage. FLAGGED OFF BY DEFAULT (MPR1-T09b, T08 finding 5): a
  // deploy without VITE_TRAY_CHECK=on must not show patients a page that
  // calls a `/tray/analyze` endpoint the production sidecar does not serve.
  // The matching route gate is `router/RequireTrayCheck.tsx`.
  { to: '/dashboard/tray-check', labelKey: 'nav.trayCheck', icon: Grid3x3, enabled: isTrayCheckEnabled },
  { to: '/dashboard/medications', labelKey: 'nav.medications', icon: Pill },
  { to: '/dashboard/qa', labelKey: 'nav.qa', icon: MessageCircleQuestion },
  { to: '/dashboard/safety', labelKey: 'nav.safety', icon: Shield },
  { to: '/dashboard/education', labelKey: 'nav.education', icon: BookOpen },
  { to: '/dashboard/profile', labelKey: 'nav.profile', icon: User },
  { to: '/dashboard/settings', labelKey: 'nav.settings', icon: Settings },
];

const ADMIN_MENU_ITEMS: MenuItem[] = [
  { to: '/admin/dashboard', labelKey: 'nav.adminPanel', icon: ShieldCheck },
  { to: '/admin/users', labelKey: 'nav.adminUsers', icon: Users },
  { to: '/admin/sidecar', labelKey: 'nav.adminSidecar', icon: Server },
];

/** Single navy top navbar rendered on EVERY page, public and authenticated
 * (Phase 6 -- Muthu's decision: the desktop Sidebar + Topbar are deleted,
 * this replaces both). Evolved from PublicLayout's original header so the
 * About dropdown / mobile hamburger pattern carries over unchanged; the
 * signed-in "Menu" dropdown is new, and absorbs Topbar's LanguageSwitcher +
 * voice toggle + avatar. Logo always routes to "/" (public home) even from
 * inside the dashboard -- restores the previously-missing route-back-to-home. */
export default function Navbar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === 'ADMIN';
  const { logout } = useAuth();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const aboutMenuRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVoiceEnabled(voice.isEnabled());
    return voice.subscribe(setVoiceEnabled);
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (aboutMenuRef.current && !aboutMenuRef.current.contains(e.target as Node)) setAboutOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  // Close any open menu/panel on navigation -- avoids a stale dropdown
  // staying open after one of its own links was just used.
  useEffect(() => {
    setAboutOpen(false);
    setMenuOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  // Flag-gated entries are dropped here, on every render, so a build without
  // the flag has no link to them at all (desktop dropdown AND mobile panel).
  const menuItems = MENU_ITEMS.filter((item) => item.enabled?.() ?? true);

  const isAboutActive = pathname === '/about' || pathname.startsWith('/about/');
  const initials = user?.first_name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?';
  const displayName = user?.first_name ? `${user.first_name} ${user.last_name ?? ''}`.trim() : user?.email;

  const voiceButton = (mobile: boolean) => (
    <button
      type="button"
      onClick={() => voice.toggle()}
      aria-label={voiceEnabled ? t('nav.voiceOn') : t('nav.voiceOff')}
      title={t('nav.voiceToggle')}
      className={`rounded-xl border flex items-center justify-center transition-colors shrink-0 ${
        mobile ? 'h-11 w-11' : 'h-10 w-10'
      } ${
        voiceEnabled
          ? 'bg-teal-500/20 border-teal-300/50 text-teal-200'
          : 'bg-white/5 border-white/15 text-white/60 hover:text-white hover:border-white/30'
      }`}
    >
      {voiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
    </button>
  );

  return (
    <header className="sticky top-0 z-40 bg-navy border-b border-white/10">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2.5 focus-visible:ring shrink-0">
          <Logo onDark className="h-7" />
        </Link>

        {/* Desktop nav */}
        <nav className="hidden sm:flex items-center gap-3">
          <div className="relative" ref={aboutMenuRef}>
            <button
              type="button"
              onClick={() => {
                setAboutOpen((v) => !v);
                setMenuOpen(false);
              }}
              aria-expanded={aboutOpen}
              aria-haspopup="true"
              className={`flex items-center gap-1 text-sm font-medium transition-colors py-2 px-1 min-h-[44px] ${
                isAboutActive ? 'text-white' : 'text-white/75 hover:text-white'
              }`}
            >
              {t('nav.about')} <ChevronDown className={`h-3.5 w-3.5 transition-transform ${aboutOpen ? 'rotate-180' : ''}`} />
            </button>
            {aboutOpen && (
              <div className="absolute left-0 top-full mt-1 w-64 bg-white rounded-xl shadow-lg border border-slate-100 py-2 animate-fade-in z-50">
                {ABOUT_PAGES.map((p) => (
                  <Link
                    key={p.id}
                    to={p.href}
                    className="block px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 hover:text-navy transition-colors"
                  >
                    {t(p.labelKey)}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {isAuthenticated ? (
            <>
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen((v) => !v);
                    setAboutOpen(false);
                  }}
                  aria-expanded={menuOpen}
                  aria-haspopup="true"
                  className="flex items-center gap-1 text-sm font-medium text-white/75 hover:text-white transition-colors py-2 px-1 min-h-[44px]"
                >
                  {t('nav.menu')} <ChevronDown className={`h-3.5 w-3.5 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-72 bg-white rounded-xl shadow-lg border border-slate-100 py-2 animate-fade-in z-50 max-h-[calc(100vh-5rem)] overflow-y-auto">
                    {menuItems.map(({ to, labelKey, icon: Icon, end }) => (
                      <NavLink
                        key={to}
                        to={to}
                        end={end}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                            isActive ? 'text-navy bg-teal-50 font-semibold' : 'text-slate-700 hover:bg-slate-50 hover:text-navy'
                          }`
                        }
                      >
                        <Icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
                        {t(labelKey)}
                      </NavLink>
                    ))}
                    {isAdmin && (
                      <div className="border-t border-slate-100 mt-2 pt-2">
                        <p className="px-4 pb-1.5 text-xs font-semibold text-amber-600 uppercase tracking-wider">{t('nav.admin')}</p>
                        {ADMIN_MENU_ITEMS.map(({ to, labelKey, icon: Icon }) => (
                          <NavLink
                            key={to}
                            to={to}
                            className={({ isActive }) =>
                              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                                isActive ? 'text-amber-800 bg-amber-50 font-semibold' : 'text-amber-700 hover:bg-amber-50'
                              }`
                            }
                          >
                            <Icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
                            {t(labelKey)}
                          </NavLink>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <LanguageSwitcher />
              {voiceButton(false)}

              <div className="flex items-center gap-2 pl-1">
                <div className="h-9 w-9 rounded-full bg-white/15 border border-white/25 flex items-center justify-center shrink-0">
                  <span className="text-white text-xs font-bold">{initials}</span>
                </div>
                <span className="hidden lg:inline text-sm text-white/85 font-medium max-w-[10rem] truncate">
                  {displayName}
                </span>
              </div>

              <button
                type="button"
                onClick={() => logout()}
                className="flex items-center gap-1.5 text-sm font-medium text-white/75 hover:text-white transition-colors py-2 px-1 min-h-[44px]"
              >
                <LogOut className="h-4 w-4" /> {t('nav.signOut')}
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-white/75 hover:text-white min-h-[44px] flex items-center">
                {t('nav.signIn')}
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center gap-2 bg-coral hover:bg-coral/90 text-white px-4 py-2 rounded-xl font-semibold text-sm transition-colors min-h-[44px]"
              >
                {t('nav.getStarted')}
              </Link>
            </>
          )}
        </nav>

        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
          className="sm:hidden h-11 w-11 flex items-center justify-center rounded-xl text-white hover:bg-white/10 shrink-0"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile panel */}
      {mobileOpen && (
        <nav className="sm:hidden border-t border-white/10 px-6 py-4 flex flex-col gap-1 bg-navy max-h-[calc(100vh-4rem)] overflow-y-auto">
          <p className="text-[11px] font-semibold text-white/40 uppercase tracking-wider pt-1 pb-1.5">{t('nav.about')}</p>
          {ABOUT_PAGES.map((p) => (
            <Link key={p.id} to={p.href} className="text-sm font-medium text-white/80 hover:text-white py-2.5 min-h-[44px] flex items-center">
              {t(p.labelKey)}
            </Link>
          ))}

          {isAuthenticated && (
            <div className="border-t border-white/10 mt-1 pt-2">
              <p className="text-[11px] font-semibold text-white/40 uppercase tracking-wider pb-1.5">{t('nav.menu')}</p>
              {menuItems.map(({ to, labelKey, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex items-center gap-3 text-sm font-medium py-2.5 min-h-[44px] transition-colors ${
                      isActive ? 'text-white' : 'text-white/80 hover:text-white'
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
                  {t(labelKey)}
                </NavLink>
              ))}
              {isAdmin && (
                <>
                  <p className="text-[11px] font-semibold text-amber-400/80 uppercase tracking-wider pb-1.5 pt-2">{t('nav.admin')}</p>
                  {ADMIN_MENU_ITEMS.map(({ to, labelKey, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      className="flex items-center gap-3 text-sm font-medium py-2.5 min-h-[44px] text-amber-300 hover:text-amber-200 transition-colors"
                    >
                      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
                      {t(labelKey)}
                    </NavLink>
                  ))}
                </>
              )}
            </div>
          )}

          <div className="pt-3 mt-2 border-t border-white/10 flex flex-col gap-2">
            {isAuthenticated ? (
              <>
                <div className="flex items-center justify-between gap-3 py-2">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-full bg-white/15 border border-white/25 flex items-center justify-center shrink-0">
                      <span className="text-white text-xs font-bold">{initials}</span>
                    </div>
                    <span className="text-sm text-white/85 font-medium truncate">{displayName}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <LanguageSwitcher />
                    {voiceButton(true)}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => logout()}
                  className="flex items-center justify-center gap-2 border border-white/30 text-white py-3 rounded-xl font-semibold min-h-[44px]"
                >
                  <LogOut className="h-4 w-4" /> {t('nav.signOut')}
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="border border-white/30 text-white text-center py-3 rounded-xl font-semibold min-h-[44px] flex items-center justify-center"
                >
                  {t('nav.signIn')}
                </Link>
                <Link
                  to="/register"
                  className="bg-coral text-white text-center py-3 rounded-xl font-semibold min-h-[44px] flex items-center justify-center"
                >
                  {t('nav.getStarted')}
                </Link>
              </>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
