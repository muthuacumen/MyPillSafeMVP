/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Feature flag, default OFF. Exactly "on" reveals the tray-check page (nav
   * entry + route); see src/lib/featureFlags.ts. */
  readonly VITE_TRAY_CHECK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
