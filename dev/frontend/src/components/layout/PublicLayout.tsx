import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { AppFooter } from './AppFooter';
import { AssistantWidget } from '@/components/AssistantWidget';

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
      <AssistantWidget />
    </div>
  );
}
