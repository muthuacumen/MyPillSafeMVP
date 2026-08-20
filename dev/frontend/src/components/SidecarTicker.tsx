import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { statusApi, type PublicSidecarStatus } from '@/api/status';

const POLL_MS = 30_000;

/** Slim, full-width scrolling marquee polling the NO-AUTH `GET
 * /status/sidecar` (Task T2/T3) -- mounted in both AppShell and PublicLayout
 * so every page (signed in or not) shows whether the analysis engine is up.
 *
 * Fails silent by design: a transient poll failure never removes an
 * already-shown ticker (no reason to flash it away over one dropped
 * request), but until the FIRST call ever succeeds this renders nothing --
 * never a broken/empty bar reserving layout space. */
export function SidecarTicker() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<PublicSidecarStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = () => {
      statusApi
        .getSidecarStatus()
        .then(({ data }) => {
          if (!cancelled) setStatus(data);
        })
        .catch(() => {
          // Silent by design (see doc comment) -- keep whatever was last
          // shown rather than blanking the bar on one dropped request.
        });
    };

    poll();
    const id = window.setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (!status) return null;

  const tone = status.sidecar_up ? 'sidecar-ticker-up' : 'sidecar-ticker-down';

  return (
    <div
      className={`sidecar-ticker ${tone}`}
      role="status"
      aria-live="polite"
      aria-label={t('sidecarTicker.label')}
    >
      <div className="sidecar-ticker-track">
        <span className="sidecar-ticker-item">{status.message}</span>
        {/* Exact duplicate of the item above, hidden from assistive tech --
            the CSS keyframe scrolls exactly one copy's width (translateX
            -50%) so the loop is seamless. Reduced-motion mode hides this
            second copy entirely and falls back to static text (globals.css). */}
        <span className="sidecar-ticker-item" aria-hidden="true">
          {status.message}
        </span>
      </div>
    </div>
  );
}

export default SidecarTicker;
