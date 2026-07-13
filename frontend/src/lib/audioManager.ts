// Global singleton AudioManager to handle persistent background audio playback across routes.
class AudioManager {
  private audio: HTMLAudioElement | null = null;
  private currentUrl: string | null = null;
  private currentTrackId: string | null = null;
  private listeners: Set<(state: { isPlaying: boolean; trackId: string | null }) => void> = new Set();

  public play(trackId: string, url: string) {
    if (this.currentTrackId === trackId && this.audio) {
      if (this.audio.paused) {
        this.audio.play().catch(err => console.error("Audio resume failed:", err));
        this.notify();
      }
      return;
    }

    this.stop();

    this.currentTrackId = trackId;
    this.currentUrl = url;
    this.audio = new Audio(url);
    this.audio.loop = true;

    this.audio.addEventListener('play', () => this.notify());
    this.audio.addEventListener('pause', () => this.notify());

    this.audio.play().catch(err => {
      console.error("Audio playback failed:", err);
      this.notify();
    });

    this.notify();
  }

  public pause() {
    if (this.audio) {
      this.audio.pause();
    }
  }

  public stop() {
    if (this.audio) {
      this.audio.pause();
      this.audio = null;
    }
    this.currentTrackId = null;
    this.currentUrl = null;
    this.notify();
  }

  public isPlaying(trackId?: string): boolean {
    if (!this.audio) return false;
    if (trackId && this.currentTrackId !== trackId) return false;
    return !this.audio.paused;
  }

  public getCurrentTrackId(): string | null {
    return this.currentTrackId;
  }

  public subscribe(listener: (state: { isPlaying: boolean; trackId: string | null }) => void) {
    this.listeners.add(listener);
    listener({ isPlaying: this.isPlaying(), trackId: this.currentTrackId });
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    const state = { isPlaying: this.isPlaying(), trackId: this.currentTrackId };
    this.listeners.forEach(listener => listener(state));
  }
}

export const audioManager = new AudioManager();
