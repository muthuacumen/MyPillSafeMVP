import i18n from '@/i18n';
import type { TrayMsg } from '@/types';

/**
 * Renders a backend-provided `Msg` (tray/pill message contract:
 * `{key, params, default_en, provisional}`) through the i18n layer.
 *
 * WHY NOT `t(msg.key)`: backend message keys are FLAT, pre-namespaced
 * identifiers, not a nesting hint. `tray_messages.py::TrayMsgKey` declares
 * "tray.slot.abstain" (a leaf message) and "tray.slot.abstain.ask_to_flip"
 * (an unrelated sibling, not its child) side by side. i18next's default `t()`
 * splits a key on "." and walks the resource tree segment by segment, so it
 * cannot resolve "tray.slot.abstain.ask_to_flip" once "tray.slot.abstain" is
 * itself a string leaf a segment above it -- the walk dies trying to read a
 * property off a string. Every one of these backend keys is stored instead as
 * a literal, non-nested property name (dots and all) on the `msgCatalog`
 * object in `i18n/locales/{en,fr}.json`, and looked up here by direct object
 * access -- still driven by the active language and the same resource
 * bundles i18next loaded (this IS the i18n layer), just not through `t()`'s
 * path-splitting shorthand.
 *
 * Falls back to `msg.default_en` whenever the current language's bundle has
 * no entry for `msg.key` -- covers a genuinely unknown/future backend key,
 * not (in practice) the 9 PROVISIONAL keys the T04 brief named, all of which
 * are wired into both `msgCatalog.en` and `msgCatalog.fr` below.
 */
export function resolveTrayMsg(msg: TrayMsg | null | undefined): string | null {
  if (!msg) return null;
  const lang = i18n.resolvedLanguage ?? i18n.language ?? 'en';
  const bundle = i18n.getResourceBundle(lang, 'translation') as
    | { msgCatalog?: Record<string, string> }
    | undefined;
  const template = bundle?.msgCatalog?.[msg.key];
  return interpolate(template ?? msg.default_en, msg.params);
}

/** i18next's own `{{var}}` interpolation syntax, applied manually since this
 * path bypasses `t()`. None of the current catalog copy uses a placeholder
 * (backend params exist for future/debug use, not today's copy), so this is
 * forward-compatible plumbing more than an exercised feature today. */
function interpolate(text: string, params?: Record<string, unknown> | null): string {
  if (!params) return text;
  return text.replace(/\{\{\s*(\w+)\s*\}\}/g, (whole, key: string) =>
    key in params ? String(params[key]) : whole,
  );
}
