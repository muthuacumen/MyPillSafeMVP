import { useEffect, useState } from 'react';
import { CheckCircle2, Search, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { referenceApi } from '@/api/reference';
import type { DinSuggestion } from '@/types';

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

/** Per-medication "Is this your medication?" confirm step (Phase 2). Shows
 * suggested product name + strength + DIN with one-tap Confirm, a "pick a
 * different one" search box backed by `/reference/search`, and (depending
 * on context) "skip for now" / "never mind". Never auto-commits a
 * suggestion — every DIN link requires an explicit tap. */
export function DinLinkPanel({
  drugName,
  dosage,
  initialSuggestions,
  onConfirm,
  onSkip,
  onCancel,
}: DinLinkPanelProps) {
  const [suggestions, setSuggestions] = useState<DinSuggestion[]>(initialSuggestions ?? []);
  const [loadingSuggestions, setLoadingSuggestions] = useState(!initialSuggestions);
  const [showSearch, setShowSearch] = useState(!initialSuggestions || initialSuggestions.length === 0);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DinSuggestion[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [savingDin, setSavingDin] = useState<string | null>(null);
  const [error, setError] = useState('');

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
      setError('Could not save that selection. Please try again.');
    } finally {
      setSavingDin(null);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const { data } = await referenceApi.search(query.trim());
      setSearchResults(data);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
      <p className="text-sm font-semibold text-slate-900">Is this your medication?</p>

      {loadingSuggestions && <p className="text-xs text-slate-500">Looking up matching products…</p>}

      {!showSearch && suggestions.length > 0 && (
        <div className="space-y-2">
          {suggestions.slice(0, 3).map((s) => (
            <div
              key={s.din}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3"
            >
              <div>
                <p className="text-sm font-semibold text-slate-900">{s.product}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {s.strength ? `${s.strength} · ` : ''}DIN {s.din}
                </p>
              </div>
              <Button size="sm" loading={savingDin === s.din} onClick={() => handleConfirm(s.din)}>
                <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
              </Button>
            </div>
          ))}
        </div>
      )}

      {!showSearch && (
        <div className="flex flex-wrap gap-4 pt-1">
          <button
            type="button"
            className="text-xs font-semibold text-teal-700 underline"
            onClick={() => setShowSearch(true)}
          >
            Pick a different one
          </button>
          {onSkip && (
            <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onSkip}>
              Skip for now
            </button>
          )}
        </div>
      )}

      {showSearch && (
        <div className="space-y-2">
          <div className="flex gap-2 items-start">
            <div className="flex-1">
              <Input
                placeholder="Search by medication name"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                icon={<Search className="h-4 w-4" />}
              />
            </div>
            <Button size="sm" loading={searching} onClick={handleSearch}>
              Search
            </Button>
          </div>

          {searchResults !== null && searchResults.length === 0 && (
            <p className="text-xs text-slate-500">No matches. Try a different spelling.</p>
          )}

          {searchResults && searchResults.length > 0 && (
            <div className="space-y-2">
              {searchResults.map((s) => (
                <div
                  key={s.din}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{s.product}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {s.strength ? `${s.strength} · ` : ''}DIN {s.din}
                    </p>
                  </div>
                  <Button size="sm" loading={savingDin === s.din} onClick={() => handleConfirm(s.din)}>
                    <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-4">
            {suggestions.length > 0 && (
              <button
                type="button"
                className="text-xs font-semibold text-slate-500 underline"
                onClick={() => setShowSearch(false)}
              >
                Back to suggestions
              </button>
            )}
            {onSkip && (
              <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onSkip}>
                Skip for now
              </button>
            )}
            {onCancel && (
              <button type="button" className="text-xs font-semibold text-slate-500 underline" onClick={onCancel}>
                Never mind
              </button>
            )}
          </div>
        </div>
      )}

      {error && <p className="text-xs text-danger-text">{error}</p>}

      <p className="flex items-start gap-1.5 text-[11px] text-slate-400 border-t border-slate-200 pt-2">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        Decision-support only — not medical advice. Verify with a pharmacist.
      </p>
    </div>
  );
}
