/**
 * Web Audio API based queue player to play back streamed audio chunks gaplessly.
 */
export class AudioQueuePlayer {
  constructor() {
    this.audioCtx = null;
    this.nextPlayTime = 0;
    this.sourceNodes = [];
    this.onSentenceStart = null; // Callback for UI highlight
    this.onPlaybackComplete = null; // Callback when all queued audio finishes playing
    this.completionTimeout = null;
  }

  /**
   * Initializes the AudioContext on user interaction.
   */
  init() {
    if (!this.audioCtx) {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      this.nextPlayTime = this.audioCtx.currentTime;
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  /**
   * Enqueues a base64 encoded 16-bit PCM chunk.
   * @param {string} base64Audio - Base64 encoded PCM 16-bit samples.
   * @param {number} sampleRate - Sample rate of the audio (e.g. 24000).
   * @param {string} text - The transcription associated with the audio.
   */
  enqueue(base64Audio, sampleRate = 24000, text = "") {
    this.init();

    if (this.completionTimeout) {
      clearTimeout(this.completionTimeout);
      this.completionTimeout = null;
    }

    try {
      // Decode Base64 string to bytes
      const binaryString = window.atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert 16-bit PCM bytes to float32 [-1.0, 1.0]
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      // Create Web Audio Buffer
      const audioBuffer = this.audioCtx.createBuffer(1, float32Array.length, sampleRate);
      audioBuffer.copyToChannel(float32Array, 0);

      // Create Buffer Source Node
      const source = this.audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioCtx.destination);

      const now = this.audioCtx.currentTime;
      // If next play time has passed, schedule immediately with a tiny buffer safety delay
      if (this.nextPlayTime < now) {
        this.nextPlayTime = now + 0.05; // 50ms scheduling gap
      }

      const playTime = this.nextPlayTime;
      source.start(playTime);
      this.sourceNodes.push(source);

      // Schedule callback when this particular sentence is about to play
      if (this.onSentenceStart && text) {
        const delayMs = (playTime - now) * 1000;
        setTimeout(() => {
          if (this.onSentenceStart) {
            this.onSentenceStart(text);
          }
        }, Math.max(0, delayMs));
      }

      // Update nextPlayTime based on buffer duration
      this.nextPlayTime += audioBuffer.duration;

      // Cleanup finished sources & check playback completion
      source.onended = () => {
        const idx = this.sourceNodes.indexOf(source);
        if (idx > -1) {
          this.sourceNodes.splice(idx, 1);
        }

        if (this.sourceNodes.length === 0) {
          const remainingTimeMs = Math.max(0, (this.nextPlayTime - this.audioCtx.currentTime) * 1000);
          if (this.completionTimeout) clearTimeout(this.completionTimeout);
          this.completionTimeout = setTimeout(() => {
            if (this.sourceNodes.length === 0 && this.onPlaybackComplete) {
              this.onPlaybackComplete();
            }
          }, remainingTimeMs + 50);
        }
      };

    } catch (e) {
      console.error("Error decoding or scheduling audio chunk", e);
    }
  }

  /**
   * Returns true if audio is actively playing or queued to play.
   */
  get isPlaying() {
    return this.sourceNodes.length > 0 || (this.audioCtx && this.nextPlayTime > this.audioCtx.currentTime);
  }

  /**
   * Instantly stops all playing and scheduled audio.
   */
  stop() {
    if (this.completionTimeout) {
      clearTimeout(this.completionTimeout);
      this.completionTimeout = null;
    }
    this.sourceNodes.forEach(node => {
      try {
        node.stop();
      } catch (e) {
        // Source node might not have started or already stopped
      }
    });
    this.sourceNodes = [];
    this.nextPlayTime = this.audioCtx ? this.audioCtx.currentTime : 0;
  }
}
