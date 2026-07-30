import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2, Factory, Search, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { referenceApi } from '@/api/reference';
import type { DinSuggestion, NameMatch } from '@/types';

interface DinLinkPanelProps {
  drugName: string;
  dosage?: string | null;
  /** Suggestions already fetched at prescription-save time (Phase 2 auto-
   * match). When omitted, the panel runs its own search on mount using
   * `drugName`/`dosage` — this is what lets the edit-medication flow reuse
   * the exact same confirm/search UI without a fresh scan. */
  initialSuggestions?: DinSuggestion[];
  onConfirm: (din: string) => Promise<void> | void;
  /** "skip for now" — only rendered when provided (post-scan flow). */
  onSkip?: () => void;
  /** "never mind" — closes the panel without changing anything (edit flow). */
  onCancel?: () => void;
}

const matchOf = (s: DinSuggestion): NameMatch => s.name_match ?? 'exact';

/** Per-medication "Is this your medication?" confirm step (Phase 2). Shows
 * suggested product name + strength + DIN with one-tap Confirm, a "pick a
 * different one" search box backed by `/reference/search`, and (depending
 * on context) "skip for now" / "never mind". Never auto-commits a
 * suggestion — every DIN link requires an explicit tap.
 *
 * LOOK-ALIKE GATE (2026-07-30). When NO candidate on offer keeps every word
 * the label printed, one tap is too few. That is the measured ZOLTIRAX →
 * ZOVIRAX and TYLENOL PM → TYLENOL EXTRA STRENGTH state, and no search score
 * can detect it — the second scores a perfect 100.0, because rapidfuzz's
 * `token_set_ratio` compares the token intersection and so rates a query
 * that is a strict superset of the product name as highly as an exact match.
 * In that state the panel names the missing word and disables Confirm until
 * the user acknowledges having checked the label. Candidates are still shown
 * and still linkable: a wrong DIN feeds SB2 a wrong appearance row and BB3 a
 * wrong monograph, but hiding the near-match would also block recovery from
 * OCR noise, and DIN linking is offered, never mandatory. */
export function DinLinkPanel({
  drugName,
  dosage,
  initialSuggestions,
  onConfirm,
  onSkip,
  onCancel,
}: DinLinkPanelProps) {
  const { t } = useTranslation();
  const [suggestions, setSuggestions] = useState<DinSuggestion[]>(initialSuggestions ?? []);
  const [loadingSuggestions, setLoadingSuggestions] = useState(!initialSuggestions);
  const [showSearch, setShowSearch] = useState(!initialSuggestions || initialSuggestions.length === 0);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DinSuggestion[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [savingDin, setSavingDin] = useState<string | null>(null);
  const [error, setError] = useState('');
  // Reset whenever the displayed candidate set changes -- an acknowledgement
  // is about one specific list of names, never a standing permission.
  const [ackLookAlike, setAckLookAlike] = useState(false);

  useEffect(() => {
    if (initialSuggestions) return;
    let cancelled = false;
    setLoadingSuggestions(true);
    referenceApi
      .search([drugName, dosage].filter(Boolean).join(' '))
      .then(({ data }) => {
        if (cancelled) return;
        setSuggestions(data);
        setShowSearch(data.length === 0);
      })
      .catch(() => {
        if (!cancelled) setShowSearch(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingSuggestions(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConfirm = async (candidateDin: string) => {
    setSavingDin(candidateDin);
    setError('');
    try {
      await onConfirm(candidateDin);
    } catch {
      setError(t('din.saveError'));
    } finally {
      setSavingDin(null);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setAckLookAlike(false);
    try {
      const { data } = await referenceApi.search(query.trim());
      setSearchResults(data);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  /** One candidate list, plus the look-alike gate when it needs one. Used for
   * both the scan-time suggestions and the manual search results, because the
   * same wrong tap is available in both. */
  const renderCandidates = (list: DinSuggestion[], labelName: string) => {
    const gated = list.length > 0 && !list.some((s) => matchOf(s) === 'exact');
    const missing = [...new Set(list.flatMap((s) => s.missing_tokens ?? []))];

    return (
      <div className="space-y-2">
        {gated && (
          <div className="rounded-lg border-2 border-amber-400 bg-amber-50 p-3 space-y-2">
            <p className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {t('din.lookAlike.title')}
            </p>
            <p className="text-xs text-amber-900 leading-relaxed">
              {t('din.lookAlike.body', {
                label: labelName,
                tokens: missing.join(', '),
              })}
            </p>
            <label className="flex items-center gap-2 text-xs font-semibold text-amber-900 cursor-pointer min-h-[44px]">
              <input
                type="checkbox"
                className="h-5 w-5 shrink-0 accent-teal-600"
                checked={ackLookAlike}
                onChange={(e) => setAckLookAlike(e.target.checked)}
              />
              <span>{t('din.lookAlike.acknowledge')}</span>
            </label>
          </div>
        )}

        {list.map((s) => {
          const match = matchOf(s);
          return (
            <div
              key={s.din}
              className={`flex items-center justify-between gap-3 rounded-lg border bg-white p-3 ${
                match === 'look_alike' ? 'border-amber-300' : 'border-slate-200'
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900 break-words">{s.product}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {s.strength ? `${s.strength} · ` : ''}DIN {s.din}
                </p>
                {match === 'look_alike' && (s.missing_tokens?.length ?? 0) > 0 && (
                  <p className="text-xs font-semibold text-amber-800 mt-1 flex items-start gap-1">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-px" />
                    {t('din.lookAlike.rowBadge', { tokens: s.missing_tokens!.join(', ') })}
                  </p>
                )}
                {match === 'manufacturer' && (
                  <p className="text-xs text-slate-600 mt-1 flex items-start gap-1">
                    <Factory className="h-3.5 w-3.5 shrink-0 mt-px" />
                    {t('din.differentMaker')}
                  </p>
                )}
              </div>
              <Button
                size="sm"
                loading={savingDin === s.din}
                disabled={gated && !ackLookAlike}
                onClick={() => handleConfirm(s.din)}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> {t('din.confirm')}
              </Button>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
      <p className="text-sm font-semibold text-slate-900">{t('din.title')}</p>
      <p className="text-xs text-slate-500 -mt-1">{t('din.why')}</p>

      {loadingSuggestions && <p className="text-xs text-slate-500">{t('din.loading')}</p>}

      {!showSearch && suggestions.length > 0 && renderCandidates(suggestions.slice(0, 3), drugName)}

      {!showSearch && (
        <div className="flex flex-wrap gap-4 pt-1">
          <button
            type="button"
            className="text-xs font-semibold text-teal-700 underline"
            onClick={() => {
              setAckLookAlike(false);
              setShowSearch(true);
            }}
          >
            {t('din.pickDifferent')}
          </button>
          {onSkip && (
            <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onSkip}>
              {t('din.skip')}
            </button>
          )}
        </div>
      )}

      {showSearch && (
        <div className="space-y-2">
          {/* The reference tier is incomplete by construction (OTC and
              natural-health products are missing), and since the search
              gained a score cutoff an absent medication now correctly
              returns nothing at all. Say so plainly instead of presenting a
              bare search box: the medication is still saved, the user just
              loses photo verification for it. */}
          {!loadingSuggestions && suggestions.length === 0 && searchResults === null && (
            <p className="text-xs text-slate-600">{t('din.notInList')}</p>
          )}
          <div className="flex gap-2 items-start">
            <div className="flex-1">
              <Input
                placeholder={t('din.searchPlaceholder')}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                icon={<Search className="h-4 w-4" />}
              />
            </div>
            <Button size="sm" loading={searching} onClick={handleSearch}>
              {t('din.search')}
            </Button>
          </div>

          {searchResults !== null && searchResults.length === 0 && (
            <p className="text-xs text-slate-500">{t('din.noMatches')}</p>
          )}

          {searchResults && searchResults.length > 0 && renderCandidates(searchResults, query.trim())}

          <div className="flex flex-wrap gap-4">
            {suggestions.length > 0 && (
              <button
                type="button"
                className="text-xs font-semibold text-slate-500 underline"
                onClick={() => {
                  setAckLookAlike(false);
                  setShowSearch(false);
                }}
              >
                {t('din.backToSuggestions')}
              </button>
            )}
            {onSkip && (
              <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onSkip}>
                {t('din.skip')}
              </button>
            )}
            {onCancel && (
              <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onCancel}>
                {t('din.cancel')}
              </button>
            )}
          </div>
        </div>
      )}

      {error && <p className="text-xs text-danger-text">{error}</p>}

      <p className="flex items-start gap-1.5 text-[11px] text-slate-400 border-t border-slate-200 pt-2">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        {t('din.disclaimer')}
      </p>
    </div>
  );
}
