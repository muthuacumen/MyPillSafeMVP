import { Link } from 'react-router-dom';
import { Pill, ShieldAlert } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export function AppFooter() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-10">
          <div>
            <Link to="/" className="flex items-center gap-2.5 focus-visible:ring">
              <div className="h-9 w-9 rounded-xl bg-teal-600 flex items-center justify-center shrink-0">
                <Pill className="h-5 w-5 text-white" />
              </div>
              <span className="font-bold text-slate-900">PillSafe</span>
            </Link>
            <p className="text-sm text-slate-500 mt-3 max-w-xs leading-relaxed">
              AI-powered medication verification, built to prevent wrong doses, missed doses, and
              medication confusion.
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Explore</p>
            <ul className="space-y-2.5 text-sm">
              <li><Link to="/" className="text-slate-600 hover:text-teal-700 transition-colors">Home</Link></li>
              <li><Link to="/about" className="text-slate-600 hover:text-teal-700 transition-colors">About</Link></li>
              <li><Link to="/contact" className="text-slate-600 hover:text-teal-700 transition-colors">Contact</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Account</p>
            <ul className="space-y-2.5 text-sm">
              {isAuthenticated ? (
                <li><Link to="/dashboard" className="text-slate-600 hover:text-teal-700 transition-colors">Dashboard</Link></li>
              ) : (
                <>
                  <li><Link to="/login" className="text-slate-600 hover:text-teal-700 transition-colors">Sign In</Link></li>
                  <li><Link to="/register" className="text-slate-600 hover:text-teal-700 transition-colors">Get Started</Link></li>
                </>
              )}
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-start gap-2 text-xs text-slate-500 leading-relaxed">
            <ShieldAlert className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
            <p>
              PillSafe supports medication safety but does not replace doctors, pharmacists,
              emergency care, or prescribed medical advice.
            </p>
          </div>
          <p className="text-xs text-slate-400 sm:ml-auto sm:shrink-0">
            © {new Date().getFullYear()} PillSafe
          </p>
        </div>
      </div>
    </footer>
  );
}
