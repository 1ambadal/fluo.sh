import { useState, useEffect, useRef } from "react";
import { AudioQueuePlayer } from "../audio/audioQueuePlayer";

const getApiBaseUrl = () => {
  return `${window.location.protocol}//${window.location.host}`;
};

const getWsBaseUrl = () => {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${window.location.host}`;
};

export function useWebSocket() {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isResponding, setIsResponding] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isProcessingSpeech, setIsProcessingSpeech] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentlySpokenText, setCurrentlySpokenText] = useState("");
  const [micAmplitude, setMicAmplitude] = useState(0);

  const wsRef = useRef(null);
  const audioPlayerRef = useRef(new AudioQueuePlayer());
  const micAudioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const micProcessorRef = useRef(null);

  // Keep fresh refs for high-frequency AudioWorklet/ScriptProcessor callback
  const isRespondingRef = useRef(false);
  const isAISpeakingRef = useRef(false);

  useEffect(() => {
    isRespondingRef.current = isResponding;
  }, [isResponding]);

  useEffect(() => {
    isAISpeakingRef.current = isAISpeaking;
  }, [isAISpeaking]);

  // Initialize callbacks for sentence highlighting and TTS playback completion
  useEffect(() => {
    const player = audioPlayerRef.current;
    player.onSentenceStart = (text) => {
      setCurrentlySpokenText(text);
    };

    player.onPlaybackComplete = () => {
      setIsAISpeaking(false);
      setIsResponding(false);
      setCurrentlySpokenText("");
    };

    return () => {
      player.stop();
    };
  }, []);

  // Disconnect WebSocket and stop audio on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  const disconnect = () => {
    stopRecording();
    audioPlayerRef.current.stop();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsResponding(false);
    setIsAISpeaking(false);
    setIsProcessingSpeech(false);
    setCurrentlySpokenText("");
    setMicAmplitude(0);
    setMessages([]);
    setConversation(null);
  };

  /**
   * Starts a new conversation.
   */
  const startConversation = async (
    language,
    topic,
    initialTextMessage = null,
    proficiency = null,
    userName = null,
    autoInitiate = false,
    autoStartRecording = false
  ) => {
    disconnect();
    setIsConnecting(true);
    setMessages([]);
    setConversation(null);

    const apiBaseUrl = getApiBaseUrl();
    const wsBaseUrl = getWsBaseUrl();

    try {
      const res = await fetch(`${apiBaseUrl}/api/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language,
          topic,
          proficiency,
          user_name: userName,
        }),
      });
      
      if (!res.ok) throw new Error("Failed to create conversation");
      const convData = await res.json();
      setConversation(convData);

      const wsUrl = `${wsBaseUrl}/ws/conversation/${convData.id}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        setIsConnected(true);
        setIsConnecting(false);

        if (initialTextMessage) {
          audioPlayerRef.current.stop();
          setCurrentlySpokenText("");
          const tempId = `temp-user-${Date.now()}`;
          setMessages([
            { id: tempId, role: "user", text: initialTextMessage, feedback: null },
          ]);
          ws.send(
            JSON.stringify({
              type: "text_message",
              text: initialTextMessage,
            })
          );
        } else if (autoInitiate) {
          ws.send(
            JSON.stringify({
              type: "initiate",
            })
          );
        }

        if (autoStartRecording) {
          // Trigger recording automatically once connection opens
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            micStreamRef.current = stream;

            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            const audioCtx = new AudioCtx();
            micAudioContextRef.current = audioCtx;

            if (audioCtx.state === "suspended") {
              await audioCtx.resume();
            }

            const nativeSR = audioCtx.sampleRate;
            const targetSR = 16000;
            const source = audioCtx.createMediaStreamSource(stream);
            const processor = audioCtx.createScriptProcessor(4096, 1, 1);
            micProcessorRef.current = processor;

            processor.onaudioprocess = (e) => {
              if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
              const float32 = e.inputBuffer.getChannelData(0);

              let sum = 0;
              for (let i = 0; i < float32.length; i++) {
                sum += float32[i] * float32[i];
              }
              const rms = Math.sqrt(sum / float32.length);
              setMicAmplitude(rms);

              if (isRespondingRef.current || isAISpeakingRef.current) return;

              const ratio = nativeSR / targetSR;
              const outputLength = Math.round(float32.length / ratio);
              const resampled = new Float32Array(outputLength);
              for (let i = 0; i < outputLength; i++) {
                const srcIdx = i * ratio;
                const lo = Math.floor(srcIdx);
                const hi = Math.min(lo + 1, float32.length - 1);
                const frac = srcIdx - lo;
                resampled[i] = float32[lo] * (1 - frac) + float32[hi] * frac;
              }

              const int16 = new Int16Array(resampled.length);
              for (let i = 0; i < resampled.length; i++) {
                int16[i] = Math.max(-32768, Math.min(32767, resampled[i] * 32768));
              }

              wsRef.current.send(int16.buffer);
            };

            source.connect(processor);
            processor.connect(audioCtx.destination);
            setIsRecording(true);
          } catch (err) {
            console.error("Auto mic start error:", err);
          }
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error", err);
        setIsConnecting(false);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleIncomingMessage(data);
      };

    } catch (e) {
      console.error(e);
      setIsConnecting(false);
      alert(`Connection failed: ${e.message}`);
    }
  };

  /**
   * Loads an existing conversation.
   */
  const loadExistingConversation = async (conversationId) => {
    setIsConnecting(true);

    const apiBaseUrl = getApiBaseUrl();
    const wsBaseUrl = getWsBaseUrl();

    try {
      const res = await fetch(`${apiBaseUrl}/api/conversations/${conversationId}/messages`);
      if (!res.ok) throw new Error("Failed to load conversation history");
      const data = await res.json();

      stopRecording();
      audioPlayerRef.current.stop();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      setConversation(data.conversation);
      setMessages(data.messages || []);

      const wsUrl = `${wsBaseUrl}/ws/conversation/${conversationId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error", err);
        setIsConnecting(false);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleIncomingMessage(data);
      };

    } catch (e) {
      console.error(e);
      setIsConnecting(false);
      alert(`Failed to load conversation: ${e.message}`);
    }
  };

  /**
   * Handles messages received from backend over WebSocket.
   */
  const handleIncomingMessage = (data) => {
    switch (data.type) {
      case "processing_speech":
        setIsProcessingSpeech(true);
        break;

      case "transcription":
        setIsProcessingSpeech(false);
        if (data.text) {
          setMessages((prev) => [
            ...prev,
            { id: `temp-user-${Date.now()}`, role: "user", text: data.text, feedback: null },
          ]);
        }
        break;

      case "reply_start":
        setIsResponding(true);
        setIsAISpeaking(true);
        setCurrentlySpokenText("");
        audioPlayerRef.current.stop();
        setMessages((prev) => [
          ...prev,
          { id: "temp-assistant", role: "assistant", text: "" },
        ]);
        break;

      case "reply_chunk":
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === "temp-assistant"
              ? { ...msg, text: msg.text + data.text }
              : msg
          )
        );
        break;

      case "reply_end":
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === "temp-assistant"
              ? { ...msg, id: data.message_id }
              : msg
          )
        );
        // If no audio chunks were sent, un-mute immediately
        if (!audioPlayerRef.current.isPlaying) {
          setIsResponding(false);
          setIsAISpeaking(false);
        }
        break;

      case "audio_chunk":
        setIsAISpeaking(true);
        audioPlayerRef.current.enqueue(data.audio, data.sample_rate, data.text);
        break;

      case "feedback":
        setMessages((prev) =>
          prev.map((msg) =>
            msg.role === "user" && (msg.id === data.user_message_id || String(msg.id).startsWith("temp-user"))
              ? { ...msg, id: data.user_message_id, feedback: data.feedback }
              : msg
          )
        );
        break;

      case "error":
        console.error("Server error message:", data.message);
        setIsResponding(false);
        setIsAISpeaking(false);
        setIsProcessingSpeech(false);
        break;

      default:
        break;
    }
  };

  /**
   * Sends typed text message.
   */
  const sendTextMessage = (text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    audioPlayerRef.current.stop();
    setCurrentlySpokenText("");

    const tempId = `temp-user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: tempId, role: "user", text, feedback: null },
    ]);

    wsRef.current.send(
      JSON.stringify({
        type: "text_message",
        text: text,
      })
    );
  };

  /**
   * Starts continuous microphone recording.
   * While AI is speaking (isResponding || isAISpeaking), mic audio frames are MUTED locally
   * to prevent speaker output from feeding back into VAD.
   */
  const startRecording = async () => {
    if (micStreamRef.current) return; // Already recording
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    audioPlayerRef.current.stop();
    setCurrentlySpokenText("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      micAudioContextRef.current = audioCtx;

      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      const nativeSR = audioCtx.sampleRate;
      const targetSR = 16000;

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      micProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const float32 = e.inputBuffer.getChannelData(0);

        // Calculate live RMS amplitude for visual reactive waveform
        let sum = 0;
        for (let i = 0; i < float32.length; i++) {
          sum += float32[i] * float32[i];
        }
        const rms = Math.sqrt(sum / float32.length);
        setMicAmplitude(rms);

        // MUTE MIC INPUT while AI is generating reply or playing TTS audio
        if (isRespondingRef.current || isAISpeakingRef.current) {
          return;
        }

        // Downsample native SR → 16 kHz mono PCM
        const ratio = nativeSR / targetSR;
        const outputLength = Math.round(float32.length / ratio);
        const resampled = new Float32Array(outputLength);
        for (let i = 0; i < outputLength; i++) {
          const srcIdx = i * ratio;
          const lo = Math.floor(srcIdx);
          const hi = Math.min(lo + 1, float32.length - 1);
          const frac = srcIdx - lo;
          resampled[i] = float32[lo] * (1 - frac) + float32[hi] * frac;
        }

        const int16 = new Int16Array(resampled.length);
        for (let i = 0; i < resampled.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, resampled[i] * 32768));
        }

        wsRef.current.send(int16.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setIsRecording(true);

    } catch (err) {
      console.error("[Mic] Failed to start recording:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        alert("Microphone access denied. Please allow microphone access in browser settings.");
      }
    }
  };

  /**
   * Stops microphone recording.
   */
  const stopRecording = () => {
    if (micProcessorRef.current) {
      micProcessorRef.current.disconnect();
      micProcessorRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (micAudioContextRef.current) {
      if (micAudioContextRef.current.state !== "closed") {
        micAudioContextRef.current.close();
      }
      micAudioContextRef.current = null;
    }
    setIsRecording(false);
    setMicAmplitude(0);
  };

  // Derive explicit 4-state mic status: "listening" | "capturing" | "processing" | "ai_speaking" | "idle"
  let micState = "idle";
  if (isRecording) {
    if (isResponding || isAISpeaking) {
      micState = "ai_speaking";
    } else if (isProcessingSpeech) {
      micState = "processing";
    } else if (micAmplitude >= 0.015) {
      micState = "capturing";
    } else {
      micState = "listening";
    }
  }

  return {
    conversation,
    messages,
    isConnected,
    isConnecting,
    isResponding,
    isAISpeaking,
    isProcessingSpeech,
    isRecording,
    micAmplitude,
    micState,
    currentlySpokenText,
    startConversation,
    loadExistingConversation,
    sendTextMessage,
    startRecording,
    stopRecording,
    disconnect,
  };
}
