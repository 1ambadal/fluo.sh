import React from "react";
import { Mic, MicOff } from "lucide-react";

export function MicButton({ micState, isRecording, onToggle }) {
  const isAISpeaking = micState === "ai_speaking";

  return (
    <button
      onClick={onToggle}
      className={`simple-mic-button ${isRecording ? "active" : ""} ${isAISpeaking ? "paused" : ""}`}
      title={
        !isRecording
          ? "Click to start voice mode"
          : isAISpeaking
          ? "Fluo is speaking..."
          : "Voice mode active (Click to stop)"
      }
      aria-label="Toggle voice mode"
    >
      {isAISpeaking ? (
        <MicOff style={{ width: 16, height: 16 }} />
      ) : (
        <Mic style={{ width: 16, height: 16 }} />
      )}
      {isRecording && !isAISpeaking && <span className="simple-pulse-ring" />}
    </button>
  );
}
