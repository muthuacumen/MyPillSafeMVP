import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { AppFooter } from './AppFooter';
import BottomTabBar from './BottomTabBar';
import { DisclaimerModal } from '@/components/DisclaimerModal';
import { startDoseReminderEngine } from '@/lib/doseReminders';

// Phase 6 (Muthu's decision): the desktop Sidebar + Topbar are gone. Every
// page -- public and authenticated -- shares the same navy Navbar, and the
// shell now sits in normal document flow (sticky navbar, footer after
// content) just like PublicLayout, instead of the old fixed-height
// flex/overflow-hidden shell. Each dashboard page renders its own <h1> now
// that Topbar's page-title prop is gone.
export default function AppShell() {
  const [showDisclaimer, setShowDisclaimer] = useState(
    () => localStorage.getItem('disclaimer_accepted') !== 'true',
  );

  useEffect(() => {
    const stop = startDoseReminderEngine();
    return stop;
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <DisclaimerModal
        open={showDisclaimer}
        onAccept={() => {
          localStorage.setItem('disclaimer_accepted', 'true');
          setShowDisclaimer(false);
        }}
      />
      <Navbar />
      <main className="flex-1 p-4 sm:p-6 pb-20 md:pb-6">
        <Outlet />
      </main>
      <AppFooter />
      {/* Mobile-only fixed tab bar -- content padding above (pb-20) clears
          it; the bar itself adds env(safe-area-inset-bottom). */}
      <BottomTabBar />
    </div>
  );
}
