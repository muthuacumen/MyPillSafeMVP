const STORAGE_KEY = 'voice_enabled';

type Listener = (enabled: boolean) => void;

class VoiceAssistant {
  private listeners = new Set<Listener>();

  isEnabled(): boolean {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  }

  toggle(): boolean {
    const next = !this.isEnabled();
    localStorage.setItem(STORAGE_KEY, String(next));
    if (!next) this.stop();
    this.listeners.forEach((fn) => fn(next));
    return next;
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  speak(text: string): void {
    if (!this.isEnabled()) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    this.stop();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  }

  stop(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}

export const voice = new VoiceAssistant();
