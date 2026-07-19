import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Menu, Pill, X } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { AppFooter } from './AppFooter';

export default function PublicLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLink = (to: string, label: string, onClick?: () => void) => (
    <Link
      to={to}
      onClick={onClick}
      aria-current={pathname === to ? 'page' : undefined}
      className={`relative text-sm font-medium transition-colors py-2 ${
        pathname === to
          ? 'text-teal-700 after:absolute after:-bottom-0.5 after:left-0 after:right-0 after:h-0.5 after:rounded-full after:bg-teal-600'
          : 'text-slate-600 hover:text-teal-700'
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-sm border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-teal-600 flex items-center justify-center">
              <Pill className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-slate-900">PillSafe</span>
          </Link>

          <nav className="hidden sm:flex items-center gap-6">
            {navLink('/about', 'About')}
            {navLink('/contact', 'Contact')}
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-primary !px-4 !py-2">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-teal-700">Sign In</Link>
                <Link to="/register" className="btn-primary !px-4 !py-2">Get Started</Link>
              </>
            )}
          </nav>

          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            className="sm:hidden h-11 w-11 flex items-center justify-center rounded-xl text-slate-600 hover:bg-slate-100 focus-visible:ring"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileOpen && (
          <nav className="sm:hidden border-t border-slate-200 px-6 py-4 flex flex-col gap-1 bg-white">
            {navLink('/about', 'About', () => setMobileOpen(false))}
            {navLink('/contact', 'Contact', () => setMobileOpen(false))}
            <div className="pt-3 mt-2 border-t border-slate-100 flex flex-col gap-2">
              {isAuthenticated ? (
                <Link to="/dashboard" onClick={() => setMobileOpen(false)} className="btn-primary w-full justify-center">Dashboard</Link>
              ) : (
                <>
                  <Link to="/login" onClick={() => setMobileOpen(false)} className="btn-secondary w-full justify-center">Sign In</Link>
                  <Link to="/register" onClick={() => setMobileOpen(false)} className="btn-primary w-full justify-center">Get Started</Link>
                </>
              )}
            </div>
          </nav>
        )}
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
    </div>
  );
}
