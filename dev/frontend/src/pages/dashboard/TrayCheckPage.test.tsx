import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import i18n from '@/i18n';
import TrayCheckPage from './TrayCheckPage';
import { trayApi } from '@/api/tray';
import type { TrayAnalysisResponse } from '@/types';
import { sixRealVerifies, trayWith } from '@/test/realTraySlots';

vi.mock('@/api/tray', () => ({
  trayApi: { analyze: vi.fn() },
}));

const mockAnalyze = vi.mocked(trayApi.analyze);

/** Every slot payload in this file comes from `@/test/realTraySlots`, i.e. the
 * backend's own `slot_verdict` output. MPR1-T08 finding 2: the previous
 * fixtures built verify slots with `terminal: true`, a combination
 * `slot_verdict` never emits, which is why a reshoot-on-success bug shipped
 * under a green bar. */
function okResponse(overrides: Partial<TrayAnalysisResponse>): TrayAnalysisResponse {
  return {
    status: 'ok',
    tray: true,
    pipeline: 'nb08_tray',
    slot_count: 6,
    terminal: false,
    none_route: 'retry',
    message: null,
    profile: { profile_n: 3, supported_n: 3, unsupported_n: 0, notice: null },
    slots: sixRealVerifies(),
    timing_ms: {},
    analysis_ids: [],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TrayCheckPage />
    </MemoryRouter>,
  );
}

/** Drives CameraCapture's real denied-camera -> file-upload fallback path
 * (jsdom has no getUserMedia; src/test/setup.ts stubs it to reject, which is
 * exactly the branch CameraCapture already handles for a real denied/
 * unavailable camera). Waits for the fallback button, uploads a fake file,
 * then clicks Confirm -- the same three steps a user takes on a real denied
 * camera, exercising the actual component rather than a mock of it. */
async function captureAPhoto() {
  await screen.findByText(i18n.t('camera.uploadAPhoto'));
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File(['fake-tray-photo'], 'tray.jpg', { type: 'image/jpeg' });
  await userEvent.upload(input, file);
  const confirmBtn = await screen.findByText(i18n.t('camera.confirm'));
  await userEvent.click(confirmBtn);
}

afterEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('en');
});

describe('TrayCheckPage -- D-4 terminal-after-1-reshoot state machine', () => {
  it('bar (a): SIX CLEAN VERIFIES finish the session -- no reshoot prompt, "Check Another Tray" offered', async () => {
    mockAnalyze.mockResolvedValueOnce({ data: okResponse({}) } as never);

    renderPage();
    await captureAPhoto();

    expect(await screen.findByText(i18n.t('trayCheck.scanNewTray'))).toBeInTheDocument();
    expect(screen.queryByText(i18n.t('trayCheck.reshootTitle'))).not.toBeInTheDocument();
    expect(mockAnalyze).toHaveBeenCalledTimes(1);
  });

  it('bar (d): an unreadable slot (action flip_reshoot) offers the reshoot', async () => {
    mockAnalyze.mockResolvedValueOnce({ data: okResponse({ slots: trayWith('unreadable') }) } as never);

    renderPage();
    await captureAPhoto();

    expect(await screen.findByText(i18n.t('trayCheck.reshootTitle'))).toBeInTheDocument();
  });

  it('bar (b): a no_imprint slot at attempt 1 (none_route="retry") shows the flip/reshoot prompt instead of finishing the session', async () => {
    mockAnalyze.mockResolvedValueOnce({
      data: okResponse({ slots: trayWith('noImprintRetry') }),
    } as never);

    renderPage();
    await captureAPhoto();

    expect(mockAnalyze).toHaveBeenNthCalledWith(1, expect.anything(), 'retry');
    expect(await screen.findByText(i18n.t('trayCheck.reshootTitle'))).toBeInTheDocument();
    // The partial attempt-1 grid is still visible underneath the prompt.
    expect(screen.getByTestId('tray-slot-1')).toBeInTheDocument();
  });

  it('bar (c): a still-NONE slot at attempt 2 (none_route="terminal") renders the terminal out-of-scope message and the pharmacist hedge, and the session is done', async () => {
    mockAnalyze
      .mockResolvedValueOnce({
        data: okResponse({ slots: trayWith('noImprintRetry') }),
      } as never)
      .mockResolvedValueOnce({
        data: okResponse({ slots: trayWith('noImprintTerminal') }),
      } as never);

    renderPage();
    await captureAPhoto(); // attempt 1 -> reshoot offered
    await screen.findByText(i18n.t('trayCheck.reshootTitle'));
    await captureAPhoto(); // attempt 2 (the reshoot)

    expect(mockAnalyze).toHaveBeenNthCalledWith(2, expect.anything(), 'terminal');
    await waitFor(() => expect(screen.queryByText(i18n.t('trayCheck.reshootTitle'))).not.toBeInTheDocument());
    expect(
      screen.getByText('This pill has no markings, so MyPillSafe cannot identify it. Please check with your pharmacist.'),
    ).toBeInTheDocument();
    expect(screen.getByText(i18n.t('trayCheck.scanNewTray'))).toBeInTheDocument();
  });

  it('bar: a new upload after a completed session resets the attempt counter back to 1 (sends "retry" again, not "terminal")', async () => {
    mockAnalyze.mockResolvedValue({ data: okResponse({}) } as never);

    renderPage();
    await captureAPhoto();
    expect(mockAnalyze).toHaveBeenNthCalledWith(1, expect.anything(), 'retry');
    await screen.findByText(i18n.t('trayCheck.scanNewTray'));

    await userEvent.click(screen.getByText(i18n.t('trayCheck.scanNewTray')));
    await captureAPhoto();

    expect(mockAnalyze).toHaveBeenNthCalledWith(2, expect.anything(), 'retry');
  });
});

describe('TrayCheckPage -- profile-level notice and error states', () => {
  it('bar: a partially-unsupported profile notice renders', async () => {
    mockAnalyze.mockResolvedValueOnce({
      data: okResponse({
        profile: {
          profile_n: 4,
          supported_n: 3,
          unsupported_n: 1,
          notice: {
            key: 'pill.scope.unsupported_note',
            params: { unsupported_n: 1, profile_n: 4 },
            default_en: 'x',
            provisional: false,
          },
        },
      }),
    } as never);

    renderPage();
    await captureAPhoto();

    expect(
      await screen.findByText(
        'Some of the medications on your list are not covered by MyPillSafe yet. This pill might be one of them.',
      ),
    ).toBeInTheDocument();
  });

  it('bar: a 501 TRAY_ANALYZE_DISABLED response renders the disabled-server error state', async () => {
    mockAnalyze.mockRejectedValueOnce({
      response: { status: 501, data: { detail: { error: { code: 'TRAY_ANALYZE_DISABLED', message: 'x' } } } },
    });

    renderPage();
    await captureAPhoto();

    expect(await screen.findByText(i18n.t('trayCheck.error.disabled'))).toBeInTheDocument();
    expect(screen.getByText(i18n.t('trayCheck.tryAgain'))).toBeInTheDocument();
  });

  it('bar: a 503 BRAINS_UNAVAILABLE response renders the sidecar-down error state, distinct from the disabled-server one', async () => {
    mockAnalyze.mockRejectedValueOnce({
      response: { status: 503, data: { detail: { error: { code: 'BRAINS_UNAVAILABLE', message: 'x' } } } },
    });

    renderPage();
    await captureAPhoto();

    expect(await screen.findByText(i18n.t('trayCheck.error.brainsUnavailable'))).toBeInTheDocument();
    expect(screen.queryByText(i18n.t('trayCheck.error.disabled'))).not.toBeInTheDocument();
  });
});
