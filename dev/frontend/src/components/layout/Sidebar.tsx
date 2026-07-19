import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, ScanLine, User, Shield, BookOpen,
  LogOut, Pill, Settings, Users, MessageCircleQuestion,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const storeUser = useAuthStore((s) => s.user);
  const { t } = useTranslation();
  const isAdmin = storeUser?.role === 'ADMIN';

  const navItems = [
    { to: '/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard, end: true },
    { to: '/dashboard/analyze', label: t('nav.analyze'), icon: ScanLine, end: false },
    { to: '/dashboard/medications', label: t('nav.medications'), icon: Pill, end: false },
    { to: '/dashboard/qa', label: t('nav.qa'), icon: MessageCircleQuestion, end: false },
  ];

  const bottomItems = [
    { to: '/dashboard/profile', label: t('nav.profile'), icon: User },
    { to: '/dashboard/safety', label: t('nav.safety'), icon: Shield },
    { to: '/dashboard/education', label: t('nav.education'), icon: BookOpen },
    { to: '/dashboard/settings', label: t('nav.settings'), icon: Settings },
  ];

  const adminItems = [
    { to: '/admin/dashboard', label: t('nav.adminPanel'), icon: Settings },
    { to: '/admin/users', label: t('nav.adminUsers'), icon: Users },
  ];

  return (
    <aside className="w-64 shrink-0 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 shadow-sm">
      {/* Logo */}
      <div className="px-4 pt-6 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="h-9 w-9 rounded-xl bg-teal-600 flex items-center justify-center glow-teal">
            <Pill className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900 text-base leading-none">PillSafe</p>
            <p className="text-xs text-teal-600 mt-0.5">Medication Auditor</p>
          </div>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `nav-item ${isActive ? 'nav-item-active' : ''}`}
          >
            <Icon className="h-4 w-4" strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}

        <div className="pt-4">
          <p className="px-3 pb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {t('nav.more')}
          </p>
          {bottomItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'nav-item-active' : ''}`}
            >
              <Icon className="h-4 w-4" strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </div>

        {isAdmin && (
          <div className="pt-4">
            <p className="px-3 pb-2 text-xs font-semibold text-amber-500 uppercase tracking-wider">Admin</p>
            {adminItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'nav-item-active' : ''} ${!isActive ? 'hover:bg-amber-50 hover:text-amber-800' : ''}`
                }
              >
                <Icon className="h-4 w-4" strokeWidth={1.8} />
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </nav>

      {/* User section */}
      <div className="px-3 py-4 border-t border-slate-200 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200">
          <div className="h-8 w-8 rounded-full bg-teal-100 border border-teal-200 flex items-center justify-center shrink-0">
            <span className="text-teal-700 text-xs font-bold">
              {user?.first_name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?'}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">
              {user?.first_name ? `${user.first_name} ${user.last_name ?? ''}`.trim() : user?.email}
            </p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="nav-item w-full text-red-500 hover:text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.8} />
          {t('nav.signOut')}
        </button>
      </div>
    </aside>
  );
}
