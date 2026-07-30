import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, ScanLine, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { scansApi } from '@/api/scans';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import type { ScanRecord } from '@/types';

// The label is resolved at render time from `records.status.*` -- keeping it
// here as a literal would freeze the badge in English.
const STATUS_META: Record<ScanRecord['match_status'], { icon: typeof CheckCircle2; classes: string }> = {
  matched: { icon: CheckCircle2, classes: 'bg-success-bg text-success-text border-success-border' },
  warning: { icon: AlertTriangle, classes: 'bg-warning-bg text-warning-text border-warning-border' },
  unmatched: { icon: XCircle, classes: 'bg-danger-bg text-danger-text border-danger-border' },
};

export default function SafetyRecordsPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('nav.safety'));
  const [records, setRecords] = useState<ScanRecord[] | null>(null);

  useEffect(() => {
    scansApi.listMine().then(({ data }) => setRecords(data));
  }, []);

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">{t('nav.safety')}</h1>

      {records && records.length === 0 && (
        <Card className="text-center py-14">
          <div className="h-16 w-16 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
            <ShieldCheck className="h-8 w-8 text-teal-600" />
          </div>
          <p className="font-semibold text-slate-900">{t('records.emptyTitle')}</p>
          <p className="text-sm text-slate-500 mt-1.5">{t('records.emptyBody')}</p>
          <Link to="/dashboard/scan-pill" className="inline-block mt-5">
            <Button size="lg"><ScanLine className="h-4 w-4" /> {t('records.emptyCta')}</Button>
          </Link>
        </Card>
      )}

      {records && records.length > 0 && (
        <Card padding="none" className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">{t('records.colDate')}</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">{t('records.colDrug')}</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">{t('records.colStatus')}</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">{t('records.colAction')}</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => {
                const meta = STATUS_META[r.match_status];
                const Icon = meta.icon;
                return (
                  <tr key={r.id} className="border-b border-slate-50 last:border-0">
                    <td className="px-5 py-3 text-slate-500">{new Date(r.created_at).toLocaleString()}</td>
                    <td className="px-5 py-3 text-slate-900 font-medium">{r.drug_name ?? t('records.unknown')}</td>
                    <td className="px-5 py-3">
                      <span className={`badge border ${meta.classes}`}>
                        <Icon className="h-3 w-3 mr-1" /> {t(`records.status.${r.match_status}`)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500">{r.action_taken}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
