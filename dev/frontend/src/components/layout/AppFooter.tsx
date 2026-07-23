import { Link } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Logo } from '@/components/ui/Logo';
import { ABOUT_PAGES } from '@/components/AboutNav';

export function AppFooter() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <footer className="border-t border-white/10 bg-navy text-white">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-10">
          <div>
            <Link to="/" className="inline-flex items-center focus-visible:ring">
              <Logo onDark className="h-8" />
            </Link>
            <p className="text-sm text-white/60 mt-3 max-w-xs leading-relaxed">
              A medication-safety assistant for seniors and Canadians with language barriers —
              decision-support only.
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Explore</p>
            <ul className="space-y-2.5 text-sm">
              <li><Link to="/" className="text-white/70 hover:text-white transition-colors">Home</Link></li>
              <li><Link to="/contact" className="text-white/70 hover:text-white transition-colors">Contact</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">About</p>
            <ul className="space-y-2.5 text-sm">
              {ABOUT_PAGES.map((p) => (
                <li key={p.id}>
                  <Link to={p.href} className="text-white/70 hover:text-white transition-colors">
                    {p.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Account</p>
            <ul className="space-y-2.5 text-sm">
              {isAuthenticated ? (
                <li><Link to="/dashboard" className="text-white/70 hover:text-white transition-colors">Dashboard</Link></li>
              ) : (
                <>
                  <li><Link to="/login" className="text-white/70 hover:text-white transition-colors">Sign In</Link></li>
                  <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">Get Started</Link></li>
                </>
              )}
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-white/10 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-start gap-2 text-xs text-white/60 leading-relaxed">
            <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <p>Decision-support only — not medical advice. Always verify with a pharmacist or physician.</p>
          </div>
          <p className="text-xs text-white/40 sm:ml-auto sm:shrink-0">
            MyPillSafe · 2026 · Muthuraj Jayakumar, Sumanth Reddy, Lohith Reddy, Ali Ozdemir, Abdullah Mohammed
          </p>
        </div>
      </div>
    </footer>
  );
}
