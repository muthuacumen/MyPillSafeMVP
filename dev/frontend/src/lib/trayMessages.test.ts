import { describe, it, expect, afterEach } from 'vitest';
import i18n from '@/i18n';
import { resolveTrayMsg } from './trayMessages';
import type { TrayMsg } from '@/types';

const knownEn: TrayMsg = {
  key: 'tray.slot.verify',
  params: null,
  default_en: 'FALLBACK-SHOULD-NOT-BE-USED',
  provisional: true,
};

// The exact "abstain" vs "abstain.ask_to_flip" sibling-key collision the
// backend's TrayMsgKey namespace produces on purpose (tray_messages.py) --
// this is the scenario resolveTrayMsg's flat-lookup design exists for.
const collisionSibling: TrayMsg = {
  key: 'tray.slot.abstain.ask_to_flip',
  params: null,
  default_en: 'FALLBACK-SHOULD-NOT-BE-USED',
  provisional: true,
};

const unknownKey: TrayMsg = {
  key: 'tray.slot.some_future_key_not_in_catalog_yet',
  params: null,
  default_en: 'Please check with your pharmacist.',
  provisional: true,
};

describe('resolveTrayMsg', () => {
  afterEach(async () => {
    await i18n.changeLanguage('en');
  });

  it('bar: null message resolves to null', () => {
    expect(resolveTrayMsg(null)).toBeNull();
    expect(resolveTrayMsg(undefined)).toBeNull();
  });

  it('bar: a catalog-known key renders the catalog copy, not default_en', () => {
    const text = resolveTrayMsg(knownEn);
    expect(text).toBe('This pill matches one of the medications on your list.');
    expect(text).not.toBe(knownEn.default_en);
  });

  it('bar: a key that is a dotted sibling of a shorter leaf key still resolves correctly (the abstain / abstain.ask_to_flip collision)', () => {
    const text = resolveTrayMsg(collisionSibling);
    expect(text).toContain('other side');
    expect(text).not.toBe(collisionSibling.default_en);
  });

  it('bar: an unknown/future key falls back to default_en', () => {
    expect(resolveTrayMsg(unknownKey)).toBe('Please check with your pharmacist.');
  });

  it('bar (locale): an unknown key falls back to default_en (English) even while French is active', async () => {
    await i18n.changeLanguage('fr');
    expect(resolveTrayMsg(unknownKey)).toBe('Please check with your pharmacist.');
  });

  it('bar (locale): a catalog-known key renders French copy while French is active', async () => {
    await i18n.changeLanguage('fr');
    const text = resolveTrayMsg(knownEn);
    // FR copy for a PROVISIONAL key is flagged "(provisoire)" per the T07
    // brief's hard rule (best-effort translation, not yet reviewed).
    expect(text).toBe("Ce comprimé correspond à l'un des médicaments de votre liste. (provisoire)");
  });
});
