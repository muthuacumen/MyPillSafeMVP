import { lazy, Suspense, type ComponentType, type ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import AppShell from '@/components/layout/AppShell';
import PublicLayout from '@/components/layout/PublicLayout';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';

// Route-level code splitting — each page ships as its own chunk so a first
// visit only downloads the public/auth bundle it needs, not the whole app
// (camera capture, OCR flows, admin screens, etc.).
function lazyPage(loader: () => Promise<{ default: ComponentType }>) {
  const LazyComponent = lazy(loader);
  return (
    <Suspense fallback={<LoadingSkeleton variant="page" />}>
      <LazyComponent />
    </Suspense>
  );
}

const LoginPage = () => lazyPage(() => import('@/pages/auth/LoginPage'));
const RegisterPage = () => lazyPage(() => import('@/pages/auth/RegisterPage'));
const DashboardPage = () => lazyPage(() => import('@/pages/dashboard/DashboardPage'));
const AnalyzePage = () => lazyPage(() => import('@/pages/dashboard/AnalyzePage'));
const MyMedicationsPage = () => lazyPage(() => import('@/pages/dashboard/MyMedicationsPage'));
const QAChatPage = () => lazyPage(() => import('@/pages/dashboard/QAChatPage'));
const ProfilePage = () => lazyPage(() => import('@/pages/dashboard/ProfilePage'));
const SafetyRecordsPage = () => lazyPage(() => import('@/pages/dashboard/SafetyRecordsPage'));
const EducationPage = () => lazyPage(() => import('@/pages/dashboard/EducationPage'));
const SettingsPage = () => lazyPage(() => import('@/pages/dashboard/SettingsPage'));
const LandingPage = () => lazyPage(() => import('@/pages/public/LandingPage'));
const AboutPage = () => lazyPage(() => import('@/pages/public/AboutPage'));
const ContactPage = () => lazyPage(() => import('@/pages/public/ContactPage'));
const AdminDashboardPage = () => lazyPage(() => import('@/pages/admin/AdminDashboardPage'));
const AdminUsersPage = () => lazyPage(() => import('@/pages/admin/AdminUsersPage'));
const NotFoundPage = () => lazyPage(() => import('@/pages/NotFoundPage'));

function RequireAuth({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function RequireGuest({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" replace />;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'ADMIN') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/about', element: <AboutPage /> },
      { path: '/contact', element: <ContactPage /> },
    ],
  },
  {
    path: '/login',
    element: <RequireGuest><LoginPage /></RequireGuest>,
  },
  {
    path: '/register',
    element: <RequireGuest><RegisterPage /></RequireGuest>,
  },
  {
    path: '/dashboard',
    element: <RequireAuth><AppShell /></RequireAuth>,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'analyze', element: <AnalyzePage /> },
      { path: 'medications', element: <MyMedicationsPage /> },
      { path: 'qa', element: <QAChatPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'safety', element: <SafetyRecordsPage /> },
      { path: 'education', element: <EducationPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
  {
    path: '/admin',
    element: <RequireAdmin><AppShell /></RequireAdmin>,
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: 'dashboard', element: <AdminDashboardPage /> },
      { path: 'users', element: <AdminUsersPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
