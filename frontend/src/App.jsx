import React, { useState, useEffect, useRef } from "react";
import {
  RefreshCw, ChevronDown, ChevronUp, Terminal, MessageSquare, Plus, Mic, MicOff, Send, Play, Square, Settings, Trash2, X, AlertTriangle, PanelLeft, Menu, CornerDownLeft, ArrowUp, Sparkles, User, Radio, PhoneOff, Volume2, Keyboard, FileText
} from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { MicButton } from "./components/MicButton";

const TOPIC_POOL = [
  // Travel & Adventure
  "Ordering food at a restaurant",
  "Checking in at a hotel reception",
  "Asking for directions in a new city",
  "Buying tickets at a train station",
  "Planning a dream vacation across Europe",
  "Lost luggage at the airport customer service",
  "Renting a car in a foreign country",
  "Giving a tour of your hometown",
  "Sharing your favorite travel story",
  "Surviving a night stranded at an airport",

  // Daily Life & Socializing
  "Ordering coffee and making small talk",
  "Chatting about hobbies and weekend plans",
  "Describing your daily routine",
  "Talking about your favorite season and why",
  "Sharing childhood memories and games",
  "Discussing fitness and healthy habits",
  "Talking about your closest friends",
  "Planning a birthday surprise party",
  "Morning routines vs night owl habits",
  "How to spend a rainy Sunday afternoon",

  // Food & Cooking
  "Explaining a recipe you love step-by-step",
  "Debating the ultimate comfort food",
  "Recommending your favorite local dish",
  "Hosting a dinner party for international guests",
  "Coffee vs tea culture around the world",

  // Career & Professional
  "A mock job interview for a new role",
  "Negotiating a salary raise with a manager",
  "Pitching a startup idea to an investor",
  "Giving feedback to a colleague constructively",
  "Discussing remote work vs office work",
  "Handling a difficult customer complaint politely",

  // Entertainment, Culture & Arts
  "Talking about favorite movies or TV series",
  "Discussing a book that changed your perspective",
  "Recommending music genres and concerts",
  "Debating art, photography, and creativity",
  "Discussing video games and virtual worlds",
  "Talking about your favorite podcast",

  // Tech, Science & Future
  "Talking about technology, AI, and robots",
  "Will smartphones be replaced in 10 years?",
  "Space exploration and living on Mars",
  "How social media impacts modern life",
  "Favorite gadgets you can't live without",

  // Fun, Debates & Hypothetical
  "Debating whether cats or dogs are better",
  "If you won 10 million dollars today",
  "What superpower would you choose and why?",
  "Time travel: Past or Future?",
  "Surviving a week on a deserted island",
  "If you could meet any historical figure",
  "Is pineapple on pizza acceptable?",
  "Negotiating a price at a flea market",

  // Deep & Reflective
  "What makes a good leader?",
  "Lessons learned from a past mistake",
  "How language shapes the way we think",
  "Defining success in modern life",
  "The importance of lifelong learning",
  "Overcoming fear of public speaking",
];

function pickTopics(count = 4) {
  const shuffled = [...TOPIC_POOL].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

function App() {
  const selectedLanguage = "English";
  const [customTopic, setCustomTopic] = useState("");
  const [typedMessage, setTypedMessage] = useState("");
  const [expandedFeedbacks, setExpandedFeedbacks] = useState({});
  const [suggestedTopics, setSuggestedTopics] = useState(() => pickTopics(4));
  const [savedConversations, setSavedConversations] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const [userName, setUserName] = useState(() => localStorage.getItem("fluo_user_name") || "");
  const [userLevel, setUserLevel] = useState(() => localStorage.getItem("fluo_user_level") || "intermediate");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showTextInput, setShowTextInput] = useState(false);

  const {
    conversation,
    messages,
    isConnected,
    isConnecting,
    isResponding,
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
  } = useWebSocket();

  const messagesEndRef = useRef(null);

  const fetchConversations = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await fetch("/api/conversations");
      if (res.ok) {
        const data = await res.json();
        setSavedConversations(data);
      }
    } catch (e) {
      console.error("Failed to fetch conversations:", e);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [conversation?.id, isResponding]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isResponding]);

  const saveSettings = (name, level) => {
    setUserName(name);
    setUserLevel(level);
    localStorage.setItem("fluo_user_name", name);
    localStorage.setItem("fluo_user_level", level);
    setConfirmClear(false);
    setIsSettingsOpen(false);
  };

  const executeClearAllConversations = async () => {
    try {
      await fetch("/api/conversations", { method: "DELETE" });
      disconnect();
      fetchConversations();
      setConfirmClear(false);
      setIsSettingsOpen(false);
    } catch (e) {
      console.error("Failed to clear conversations", e);
    }
  };

  const handleStartSession = () => {
    const topic = customTopic.trim() || suggestedTopics[0];
    startConversation(selectedLanguage, topic, null, userLevel, userName, true);
  };

  const handleStartRandomSession = () => {
    const randomTopic = TOPIC_POOL[Math.floor(Math.random() * TOPIC_POOL.length)];
    startConversation(selectedLanguage, randomTopic, null, userLevel, userName, true);
  };

  const handleStartSpecificTopic = (topic) => {
    startConversation(selectedLanguage, topic, null, userLevel, userName, true);
  };

  const handleSelectSavedConversation = (convId) => {
    if (conversation?.id === convId && isConnected) return;
    loadExistingConversation(convId);
  };

  const handleShuffleSuggestions = () => {
    setSuggestedTopics(pickTopics(4));
  };

  const handleSendText = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const text = typedMessage.trim();
    if (!text) return;
    setTypedMessage("");

    if (!isConnected) {
      await startConversation(selectedLanguage, text, text, userLevel, userName, false);
    } else {
      sendTextMessage(text);
    }
  };

  const handleToggleMic = async () => {
    if (!isConnected) {
      const topic = typedMessage.trim() || null;
      await startConversation(selectedLanguage, topic, null, userLevel, userName, false, true);
    } else {
      if (isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    }
  };

  const toggleFeedbackExpand = (msgId) => {
    setExpandedFeedbacks((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const renderAssistantText = (text) => {
    if (!text) return null;
    if (currentlySpokenText && text.includes(currentlySpokenText)) {
      const parts = text.split(currentlySpokenText);
      return (
        <span>
          {parts[0]}
          <mark className="spoken-highlight">{currentlySpokenText}</mark>
          {parts.slice(1).join(currentlySpokenText)}
        </span>
      );
    }
    return <span>{text}</span>;
  };

  const isListeningGlow = micState === "listening" || micState === "capturing";

  const getTimeString = (timestamp) => {
    if (!timestamp)
      return new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return timestamp;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };



  const handleNewChat = () => {
    disconnect();
    setIsSidebarOpen(false);
  };

  return (
    <div className="app-container">
      {isSidebarOpen && (
        <div className="sidebar-overlay-trigger" onClick={() => setIsSidebarOpen(false)} />
      )}
      {/* ── Sidebar: Brand + Active Status + Saved Sessions ── */}
      <aside className={`sidebar ${!isSidebarOpen ? "collapsed" : ""}`}>
        <div className="sidebar-top">
          <div className="brand-header-row">
            <div
              className="brand-section clickable-brand"
              onClick={handleNewChat}
              title="Go to landing page"
            >
              <Terminal style={{ width: 16, height: 16, color: "var(--accent-green)" }} />
              <div>
                <h1 className="brand-title">fluo.sh</h1>
                <p className="brand-subtitle">fluent conversations</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              className="btn-toggle-sidebar"
              title="Close panel"
            >
              <PanelLeft style={{ width: 16, height: 16 }} />
            </button>
          </div>

          <button
            type="button"
            onClick={handleNewChat}
            className="btn-new-chat"
          >
            <span className="btn-new-chat-icon">
              <Plus style={{ width: 16, height: 16 }} />
            </span>
            <span>New Chat</span>
          </button>

          {/* Only Saved Sessions in sidebar if there are saved conversations */}
          {savedConversations.length > 0 && (
            <>
              <hr className="divider" />
              <div className="history-section">
                <span className="input-label">Saved Sessions</span>
                <div className="history-list margin-top-sm">
                  {savedConversations.map((conv) => {
                    const isActive = conversation?.id === conv.id;
                    return (
                      <div
                        key={conv.id}
                        onClick={() => handleSelectSavedConversation(conv.id)}
                        className={`history-item ${isActive ? "active" : ""}`}
                      >
                        <span className="history-item-topic">
                          {conv.topic || "Conversation"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
          <div className="sidebar-footer margin-top-sm">
            <button
              type="button"
              onClick={() => setIsSettingsOpen(true)}
              className="btn-settings"
            >
              <Settings style={{ width: 14, height: 14 }} />
              <span>Settings</span>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Fixed Sidebar Open Button (when on landing page and sidebar is closed) ── */}
      {!isSidebarOpen && !isConnected && !isConnecting && messages.length === 0 && !conversation && (
        <button
          type="button"
          onClick={() => setIsSidebarOpen(true)}
          className="btn-toggle-sidebar-fixed"
          title="Open Sidebar"
        >
          <PanelLeft style={{ width: 18, height: 18 }} />
        </button>
      )}

      {/* ── Main Workspace ── */}
      <main className="main-content">
        {/* Top Header (Visible during chat screen only) */}
        {(isConnected || isConnecting || messages.length > 0 || conversation) && (
          <header className="main-header">
            <div className="header-left-group">
              {!isSidebarOpen && (
                <button
                  type="button"
                  className="btn-icon-top"
                  onClick={() => setIsSidebarOpen(true)}
                  title="Open Sidebar"
                >
                  <PanelLeft style={{ width: 18, height: 18 }} />
                </button>
              )}
              {conversation?.topic && conversation.topic !== "Free Conversation" && (
                <span className="header-topic-badge">
                  {isConnected && <span className={`status-dot-top ${micState}`} />}
                  <span className="header-topic-name">
                    {conversation.topic}
                  </span>
                </span>
              )}
            </div>
          </header>
        )}

        {/* Main Body: Landing Hero OR Chat Stream */}
        <div className="chat-body">
          {!isConnected && !isConnecting && messages.length === 0 && !conversation ? (
            /* Minimal Centered Landing Page */
            <div className="landing-hero-container">
              <div className="landing-centered-brand">
                <h1 className="landing-brand-title">fluo.sh</h1>
                <p className="landing-brand-subtitle">fluent conversations</p>
              </div>

              <div className="landing-input-box-wrapper">
                <form onSubmit={handleSendText} className="landing-input-pill">
                  <input
                    type="text"
                    placeholder="say or type something..."
                    value={typedMessage}
                    onChange={(e) => setTypedMessage(e.target.value)}
                    className="landing-input-field"
                  />
                  <div className="landing-input-actions">
                    <button
                      type="button"
                      onClick={handleToggleMic}
                      className={`btn-mic-icon ${isRecording ? "recording" : ""}`}
                      title={isRecording ? "Stop listening" : "Start speaking"}
                    >
                      {isRecording ? <MicOff style={{ width: 18, height: 18 }} /> : <Mic style={{ width: 18, height: 18 }} />}
                    </button>

                    <button
                      type="submit"
                      disabled={!typedMessage.trim()}
                      className="btn-send-icon"
                      title="Send message"
                    >
                      <ArrowUp style={{ width: 16, height: 16, strokeWidth: 2.5 }} />
                    </button>
                  </div>
                </form>

                <div className="landing-surprise-me-wrapper">
                  <button
                    type="button"
                    onClick={handleStartRandomSession}
                    disabled={isConnecting}
                    className="btn-surprise-me"
                  >
                    <Sparkles style={{ width: 14, height: 14 }} />
                    <span>Surprise me</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Always Visible Chat Stream */
            <div className="messages-stream">
              {messages.map((msg) => {
                const isUser = msg.role === "user";
                const isTemp = String(msg.id).includes("temp");

                return (
                  <div
                    key={msg.id}
                    className={`chat-message-row ${isUser ? "user-row" : "assistant-row"} fade-in`}
                  >
                    <div className="chat-avatar">
                      {isUser ? <User style={{ width: 14, height: 14 }} /> : <Sparkles style={{ width: 14, height: 14 }} />}
                    </div>

                    <div className="chat-message-content">
                      <div className="chat-message-header">
                        <span className="chat-author-name">{isUser ? (userName || "You") : "Fluo"}</span>
                        <span className="chat-timestamp">{getTimeString(msg.created_at)}</span>
                      </div>

                      <div className="chat-message-bubble">
                        {isUser ? (
                          msg.text
                        ) : isTemp && !msg.text ? (
                          <span className="typing-dots">
                            <span /><span /><span />
                          </span>
                        ) : (
                          renderAssistantText(msg.text)
                        )}
                      </div>

                      {/* Compact grammar suggestion box */}
                      {isUser && msg.feedback && (msg.feedback.has_errors === true || msg.feedback.has_errors === "true" || (msg.feedback.mistakes && msg.feedback.mistakes.length > 0) || (msg.feedback.corrected_text && msg.feedback.corrected_text !== msg.text)) && (
                        <div className="grammar-compact-box fade-in-diff">
                          {msg.feedback.corrected_text && (
                            <div className="grammar-corrected-sentence">
                              <span className="grammar-sparkle-icon">✨</span>
                              <span className="grammar-corrected-text">{msg.feedback.corrected_text}</span>
                            </div>
                          )}

                          {msg.feedback.mistakes?.length > 0 && (
                            <div className="grammar-suggestions-list">
                              {msg.feedback.mistakes.map((mistake, idx) => (
                                <div key={idx} className="grammar-suggestion-item" title={mistake.explanation}>
                                  <div className="grammar-suggestion-chip">
                                    <span className="grammar-orig">{mistake.original}</span>
                                    <span className="grammar-arr">→</span>
                                    <span className="grammar-fix">{mistake.fix}</span>
                                  </div>
                                  {mistake.explanation && (
                                    <div className="grammar-chip-explanation">
                                      {mistake.explanation}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Sleek SVG Fluid Wave Ribbon (Active Chat Screen) */}
        {isConnected && (isRecording || micState === "ai_speaking" || micState === "processing") && (
          <div className={`fluid-wave-ribbon-stage fade-in ${micState}`}>
            <div className="wave-ribbon-capsule">
              <svg className="wave-svg" viewBox="0 0 320 36">
                <defs>
                  <linearGradient id="waveGradUser" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity="0.9" />
                    <stop offset="50%" stopColor="#06b6d4" stopOpacity="1" />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.9" />
                  </linearGradient>
                  <linearGradient id="waveGradAI" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.9" />
                    <stop offset="50%" stopColor="#a855f7" stopOpacity="1" />
                    <stop offset="100%" stopColor="#ec4899" stopOpacity="0.9" />
                  </linearGradient>
                  <linearGradient id="waveGradProc" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#f97316" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#eab308" stopOpacity="0.9" />
                  </linearGradient>
                </defs>
                <path
                  className="wave-path path-1"
                  stroke={micState === "ai_speaking" ? "url(#waveGradAI)" : micState === "processing" ? "url(#waveGradProc)" : "url(#waveGradUser)"}
                  fill="none"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  d="M 0 18 Q 40 6, 80 18 T 160 18 T 240 18 T 320 18"
                />
                <path
                  className="wave-path path-2"
                  stroke={micState === "ai_speaking" ? "#a855f7" : micState === "processing" ? "#f97316" : "#06b6d4"}
                  fill="none"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  opacity="0.6"
                  d="M 0 18 Q 40 30, 80 18 T 160 18 T 240 18 T 320 18"
                />
              </svg>
            </div>
          </div>
        )}

        {/* Floating Input Bar — shown only in active sessions */}
        {(isConnected || messages.length > 0) && (
          <footer className="chat-input-footer">
            <form onSubmit={handleSendText} className="chat-input-pill">
              <textarea
                rows={1}
                placeholder="Reply to Fluo..."
                value={typedMessage}
                onChange={(e) => setTypedMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendText(e);
                  }
                }}
                className="chat-textarea"
              />
              <div className="chat-input-actions">
                {typedMessage.trim() ? (
                  <button type="submit" className="btn-send-pill" title="Send message">
                    <ArrowUp style={{ width: 18, height: 18, strokeWidth: 2.5 }} />
                  </button>
                ) : (
                  <MicButton
                    micState={micState}
                    micAmplitude={micAmplitude}
                    isRecording={isRecording}
                    onToggle={handleToggleMic}
                  />
                )}
              </div>
            </form>
          </footer>
        )}
      </main>

      {/* ── Settings Modal ── */}
      {isSettingsOpen && (
        <div className="modal-overlay" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Settings style={{ width: 18, height: 18, color: "var(--accent-green)" }} />
                <h2>Settings</h2>
              </div>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setIsSettingsOpen(false)}
              >
                <X style={{ width: 16, height: 16 }} />
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Your Name</label>
                <input
                  type="text"
                  placeholder="Enter your name..."
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="modal-input"
                />
              </div>

              <div className="form-group margin-top-sm">
                <label className="form-label">Proficiency Level</label>
                <select
                  value={userLevel}
                  onChange={(e) => setUserLevel(e.target.value)}
                  className="modal-select"
                >
                  <option value="beginner">Beginner (A1 - A2)</option>
                  <option value="intermediate">Intermediate (B1 - B2)</option>
                  <option value="advanced">Advanced (C1 - C2)</option>
                </select>
              </div>

              <div className="modal-danger-zone margin-top-md">
                <span className="input-label" style={{ color: "var(--accent-red)" }}>Danger Zone</span>
                {!confirmClear ? (
                  <button
                    type="button"
                    onClick={() => setConfirmClear(true)}
                    className="btn-clear-chats margin-top-xs"
                  >
                    <Trash2 style={{ width: 14, height: 14 }} />
                    <span>Clear All Conversations</span>
                  </button>
                ) : (
                  <div className="confirm-delete-box margin-top-xs">
                    <div className="confirm-delete-message">
                      <AlertTriangle style={{ width: 15, height: 15, color: "var(--accent-red)" }} />
                      <span>Delete all saved conversations?</span>
                    </div>
                    <div className="confirm-delete-actions">
                      <button
                        type="button"
                        onClick={() => setConfirmClear(false)}
                        className="btn-confirm-cancel"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={executeClearAllConversations}
                        className="btn-confirm-delete"
                      >
                        Yes, Delete All
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer margin-top-md">
              <button
                type="button"
                onClick={() => saveSettings(userName, userLevel)}
                className="btn-save-settings"
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
