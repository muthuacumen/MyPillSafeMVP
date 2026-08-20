import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, type RouteObject } from 'react-router-dom';
import { isValidElement } from 'react';
import { RequireTrayCheck } from './RequireTrayCheck';
import { routes } from './index';

/** MPR1-T09b, closing T08 finding 5 (frontend half): the tray-check page must
 * not exist in a deploy that did not ask for it -- neither as a nav entry
 * (Navbar.test.tsx) nor as a reachable URL (here). Flag: VITE_TRAY_CHECK,
 * default OFF, opt in with the exact value "on". */
afterEach(() => {
  vi.unstubAllEnvs();
});

function renderGuardedRoute() {
  return render(
    <MemoryRouter initialEntries={['/dashboard/tray-check']}>
      <Routes>
        <Route path="/dashboard" element={<div data-testid="dashboard-home" />} />
        <Route
          path="/dashboard/tray-check"
          element={
            <RequireTrayCheck>
              <div data-testid="tray-page" />
            </RequireTrayCheck>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

/** The `tray-check` child of the `/dashboard` branch of the REAL route table. */
function trayCheckRoute(): RouteObject {
  const dashboard = routes.find((r) => r.path === '/dashboard');
  const route = dashboard?.children?.find((c) => c.path === 'tray-check');
  if (!route) throw new Error('no tray-check route in the route table');
  return route;
}

describe('tray-check route gate (VITE_TRAY_CHECK)', () => {
  it('bar: flag UNSET (the default) -- the deep link redirects to the dashboard, the page never renders', () => {
    renderGuardedRoute();
    expect(screen.getByTestId('dashboard-home')).toBeInTheDocument();
    expect(screen.queryByTestId('tray-page')).not.toBeInTheDocument();
  });

  it('bar: flag "on" -- the page renders', () => {
    vi.stubEnv('VITE_TRAY_CHECK', 'on');
    renderGuardedRoute();
    expect(screen.getByTestId('tray-page')).toBeInTheDocument();
  });

  it('a non-"on" value ("true", "1", "false", "") never opens the route', () => {
    for (const value of ['true', '1', 'false', '', 'ON']) {
      vi.stubEnv('VITE_TRAY_CHECK', value);
      const { unmount } = renderGuardedRoute();
      expect(screen.queryByTestId('tray-page')).not.toBeInTheDocument();
      unmount();
    }
  });

  it('bar: the REAL route table wires /dashboard/tray-check through the guard, not straight to the page', () => {
    const element = trayCheckRoute().element;
    expect(isValidElement(element)).toBe(true);
    expect((element as React.ReactElement).type).toBe(RequireTrayCheck);
  });
});
