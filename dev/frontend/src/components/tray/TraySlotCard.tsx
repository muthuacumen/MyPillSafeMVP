import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2, HelpCircle, Info, ShieldAlert, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { resolveTrayMsg } from '@/lib/trayMessages';
import type { TrayAlertLevel, TraySlot, TraySlotVerdict } from '@/types';

/** Colour tokens per `alert` level -- the backend already derives this field
 * per verdict (`tray_messages.py::slot_verdict`); the card trusts it rather
 * than re-deriving a verdict->colour mapping the backend could drift out of
 * step with. Mirrors `components/ui/Alert.tsx`'s four variants exactly, incl.
 * its blue-* literal for "info" (that component has no custom `info-*`
 * token, unlike success/warning/danger). */
const ALERT_STYLES: Record<TrayAlertLevel, { wrapper: string; badge: string; icon: React.ReactNode }> = {
  ok: {
    wrapper: 'border-success-border bg-success-bg',
    badge: 'bg-success-bg text-success-text border border-success-border',
    icon: <CheckCircle2 className="h-5 w-5 text-success-text shrink-0" />,
  },
  warning: {
    wrapper: 'border-warning-border bg-warning-bg',
    badge: 'bg-warning-bg text-warning-text border border-warning-border',
    icon: <AlertTriangle className="h-5 w-5 text-warning-text shrink-0" />,
  },
  danger: {
    wrapper: 'border-danger-border bg-danger-bg',
    badge: 'bg-danger-bg text-danger-text border border-danger-border',
    icon: <XCircle className="h-5 w-5 text-danger-text shrink-0" />,
  },
  info: {
    wrapper: 'border-blue-200 bg-blue-50',
    badge: 'bg-blue-50 text-blue-800 border border-blue-200',
    icon: <Info className="h-5 w-5 text-blue-600 shrink-0" />,
  },
};

const VERDICT_LABEL_KEY: Record<TraySlotVerdict, string> = {
  verify: 'trayCheck.verdictLabel.verify',
  reject: 'trayCheck.verdictLabel.reject',
  abstain: 'trayCheck.verdictLabel.abstain',
  unreadable: 'trayCheck.verdictLabel.unreadable',
  no_imprint: 'trayCheck.verdictLabel.noImprint',
  empty: 'trayCheck.verdictLabel.empty',
  error: 'trayCheck.verdictLabel.error',
  read_only: 'trayCheck.verdictLabel.readOnly',
};

interface TraySlotCardProps {
  slot: TraySlot;
}

/** Renders ONE patient-facing slot: the verdict badge (colour from
 * `slot.alert`, label from `VERDICT_LABEL_KEY`), the slot's message and
 * notes, the pharmacist hedge on every non-verify occupied slot (Muthu's
 * binding call, T07 brief), and a supplementary recheck badge whenever
 * `contract_error` is set -- independent of whatever verdict the slot ends
 * up rendering, so it survives regardless of whether `trayContractGuard`'s
 * defense-in-depth needed to fire. Callers pass the slot through
 * `applyContractErrorGuard` first (see `TraySlotGrid`); this component does
 * not call the guard itself, so it stays a pure function of whatever slot it
 * is given -- easy to unit test with a crafted slot, guard-fired or not. */
export function TraySlotCard({ slot }: TraySlotCardProps) {
  const { t } = useTranslation();
  const style = ALERT_STYLES[slot.alert];
  const message = resolveTrayMsg(slot.message);
  const showHedge = slot.occupied && slot.verdict !== 'verify';

  return (
    <Card padding="sm" className={`space-y-2 ${style.wrapper}`} data-testid={`tray-slot-${slot.slot}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {style.icon}
          <span className="font-semibold text-slate-900 text-sm">
            {t('trayCheck.slotLabel', { n: slot.slot })}
          </span>
        </div>
        <span className={`badge ${style.badge}`}>{t(VERDICT_LABEL_KEY[slot.verdict])}</span>
      </div>

      {message && <p className="text-sm text-slate-700">{message}</p>}

      {slot.notes.length > 0 && (
        <ul className="text-xs text-slate-500 space-y-1">
          {slot.notes.map((note, i) => {
            const text = resolveTrayMsg(note);
            return text ? <li key={i}>{text}</li> : null;
          })}
        </ul>
      )}

      {slot.matched_din && (
        <p className="text-xs text-slate-500">{t('trayCheck.dinLabel', { din: slot.matched_din })}</p>
      )}

      {slot.contract_error && (
        <span className="badge bg-warning-bg text-warning-text border border-warning-border inline-flex items-center gap-1">
          <HelpCircle className="h-3.5 w-3.5" /> {t('trayCheck.contractErrorBadge')}
        </span>
      )}

      {showHedge && (
        <p className="flex items-start gap-1.5 text-xs text-slate-500 border-t border-slate-200 pt-2 mt-1">
          <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5 text-slate-400" />
          <span>{slot.pharmacist_hedge}</span>
        </p>
      )}
    </Card>
  );
}
