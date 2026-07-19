import { useEffect } from 'react';
import { voice } from '@/lib/voiceAssistant';

/** Announces a page name aloud on mount, if the voice assistant is enabled (Priority 4). */
export function useVoicePageAnnounce(pageName: string) {
  useEffect(() => {
    voice.speak(`${pageName} page loaded.`);
  }, [pageName]);
}
