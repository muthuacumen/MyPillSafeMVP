import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { DisclaimerModal } from '@/components/DisclaimerModal';
import { startDoseReminderEngine } from '@/lib/doseReminders';

const pageTitleKeys: Record<string, string> = {
  '/dashboard': 'nav.dashboard',
  '/dashboard/analyze': 'nav.analyze',
  '/dashboard/medications': 'nav.medications',
  '/dashboard/profile': 'nav.profile',
  '/dashboard/safety': 'nav.safety',
  '/dashboard/education': 'nav.education',
  '/dashboard/settings': 'nav.settings',
  '/admin/dashboard': 'admin.dashboard',
  '/admin/users': 'admin.users',
};

export default function AppShell() {
  const { pathname } = useLocation();
  const titleKey = pageTitleKeys[pathname];
  const [showDisclaimer, setShowDisclaimer] = useState(
    () => localStorage.getItem('disclaimer_accepted') !== 'true',
  );

  useEffect(() => {
    const stop = startDoseReminderEngine();
    return stop;
  }, []);

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <DisclaimerModal
        open={showDisclaimer}
        onAccept={() => {
          localStorage.setItem('disclaimer_accepted', 'true');
          setShowDisclaimer(false);
        }}
      />
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar titleKey={titleKey} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
