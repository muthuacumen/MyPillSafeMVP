import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import i18n from '@/i18n';
import Navbar from './Navbar';
import { useAuthStore } from '@/store/authStore';
import type { User } from '@/types';

/** MPR1-T09b, closing T08 finding 5 (frontend half): "Tray check" must not
 * appear in the menu of a deploy that did not set VITE_TRAY_CHECK=on. The
 * route half of the same gate is in router/RequireTrayCheck.test.tsx. */
const USER = {
  id: 'u1',
  email: 'patient@example.com',
  first_name: 'Test',
  last_name: 'Patient',
  role: 'PATIENT',
} as unknown as User;

beforeEach(() => {
  useAuthStore.setState({ user: USER, isAuthenticated: true });
});

afterEach(() => {
  vi.unstubAllEnvs();
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

/** Opens the signed-in "Menu" dropdown, where every dashboard destination
 * lives (the desktop sidebar was replaced by it in Phase 6). */
async function openMenu() {
  render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  );
  await userEvent.click(screen.getByText(i18n.t('nav.menu')));
}

describe('Navbar tray-check entry (VITE_TRAY_CHECK)', () => {
  it('bar: flag UNSET (the default) -- no tray-check entry in the menu', async () => {
    await openMenu();
    expect(screen.queryByText(i18n.t('nav.trayCheck'))).not.toBeInTheDocument();
    // Control: the rest of the menu is intact.
    expect(screen.getByText(i18n.t('nav.scanPill'))).toBeInTheDocument();
  });

  it('bar: flag "on" -- the tray-check entry is present', async () => {
    vi.stubEnv('VITE_TRAY_CHECK', 'on');
    await openMenu();
    expect(screen.getByText(i18n.t('nav.trayCheck'))).toBeInTheDocument();
  });

  it('a non-"on" value ("true") does not reveal it', async () => {
    vi.stubEnv('VITE_TRAY_CHECK', 'true');
    await openMenu();
    expect(screen.queryByText(i18n.t('nav.trayCheck'))).not.toBeInTheDocument();
  });
});
