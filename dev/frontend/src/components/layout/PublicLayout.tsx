import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { AppFooter } from './AppFooter';
import { SidecarTicker } from '@/components/SidecarTicker';

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <SidecarTicker />
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
    </div>
  );
}
