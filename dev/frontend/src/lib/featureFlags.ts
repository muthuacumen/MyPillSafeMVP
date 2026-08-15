/**
 * Build-time feature flags.
 *
 * WHY (MPR1-T08 finding 5, frontend half): the tray-check page shipped with an
 * UNCONDITIONAL nav entry and an unconditional route, so the next routine
 * deploy would have exposed it to real patients against a production sidecar
 * that has no `/tray/analyze` endpoint. A feature this young must be OFF
 * unless the deploy explicitly turns it on.
 *
 * DEFAULT OFF, OPT IN BY EXACT VALUE. Anything other than the literal string
 * "on" -- unset, empty, "false", "0", "off", "true", a typo -- leaves the
 * feature hidden. A truthiness test would have made `VITE_TRAY_CHECK=false`
 * turn the feature ON, which is the classic way a default-off flag ships
 * default-on by accident.
 *
 * READ AT CALL TIME, never captured in a module-level constant, so a caller
 * (and a test) always sees the current environment rather than whatever was
 * set the instant this module happened to be imported.
 */

/** `VITE_TRAY_CHECK=on` (localhost / demo builds only, as of MPR1). */
export function isTrayCheckEnabled(): boolean {
  return import.meta.env.VITE_TRAY_CHECK === 'on';
}
