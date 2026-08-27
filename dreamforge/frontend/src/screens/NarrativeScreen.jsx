import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamNarrativeMessage } from "../api/client";
import MessageText from "../components/MessageText";
import TypingIndicator from "../components/TypingIndicator";
import { formatMessageTime } from "../utils/time";
import { hapticImpact, hapticNotify } from "../utils/haptics";
import "./ChatScreen.css";
import "./NarrativeScreen.css";

export default function NarrativeScreen() {
  const { id: worldId } = useParams();
  const navigate = useNavigate();
  const [world, setWorld] = useState(null);
  const [narrative, setNarrative] = useState(null);
  const [entering, setEntering] = useState(true);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getWorld(worldId), api.startNarrative(worldId)]).then(([w, n]) => {
      if (!alive) return;
      setWorld(w);
      setNarrative(n);
      setEntering(false);
    });
    return () => {
      alive = false;
    };
  }, [worldId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [narrative, streamingText]);

  const send = async () => {
    const content = draft.trim();
    if (!content || sending) return;
    hapticImpact("light");
    setDraft("");
    setSending(true);
    setNarrative((n) => ({ ...n, chat_history: [...n.chat_history, { role: "user", content }] }));
    setStreamingText("");
    const controller = new AbortController();
    abortRef.current = controller;

    await streamNarrativeMessage(
      narrative.id,
      content,
      {
        onChunk: (text) => setStreamingText((prev) => prev + text),
        onDone: ({ text }) => {
          setNarrative((n) => ({ ...n, chat_history: [...n.chat_history, { role: "narrator", content: text }] }));
          setStreamingText(null);
          setSending(false);
          hapticNotify("success");
        },
        onError: (message) => {
          setNarrative((n) => ({ ...n, chat_history: [...n.chat_history, { role: "narrator", content: `⚠️ ${message}` }] }));
          setStreamingText(null);
          setSending(false);
          hapticNotify("error");
        },
        onAbort: async () => {
          setStreamingText(null);
          setSending(false);
          const fresh = await api.getNarrative(narrative.id);
          setNarrative(fresh);
        },
      },
      controller.signal
    );
  };

  const handleStop = () => {
    hapticImpact("medium");
    abortRef.current?.abort();
  };

  const handleRestart = async () => {
    setMenuOpen(false);
    hapticImpact("medium");
    await api.clearNarrative(narrative.id);
    setEntering(true);
    const fresh = await api.startNarrative(worldId);
    setNarrative(fresh);
    setEntering(false);
  };

  if (entering || !narrative || !world) {
    return (
      <div className="narrative-entering">
        <div className="narrative-entering__glyph">◈</div>
        <p>Мир пробуждается…</p>
      </div>
    );
  }

  return (
    <div className="chat-screen narrative-screen">
      <header className="chat-screen__header narrative-screen__header">
        <button className="chat-screen__back" onClick={() => navigate(-1)} aria-label="Назад">
          ‹
        </button>
        <div className="chat-screen__who">
          <span className="font-display">◈ {world.name}</span>
        </div>
        <button className="chat-screen__menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="Меню">
          ⋯
        </button>
        {menuOpen && (
          <div className="chat-screen__menu">
            <button onClick={handleRestart}>Начать историю заново</button>
          </div>
        )}
      </header>

      <div className="chat-screen__messages" ref={scrollRef}>
        {narrative.chat_history.map((m, i) => (
          <div key={i} className={"bubble-row" + (m.role === "user" ? " bubble-row--user" : "")}>
            <div className={"bubble" + (m.role === "user" ? " bubble--user" : " bubble--narrator")}>
              <div className="bubble__text">
                <MessageText content={m.content} />
              </div>
              {m.timestamp && <div className="bubble__time">{formatMessageTime(m.timestamp)}</div>}
            </div>
          </div>
        ))}
        {sending &&
          (streamingText ? (
            <div className="bubble-row">
              <div className="bubble bubble--narrator bubble--pending">
                <div className="bubble__text">
                  <MessageText content={streamingText} />
                </div>
              </div>
            </div>
          ) : (
            <div className="bubble-row">
              <TypingIndicator />
            </div>
          ))}
      </div>

      <div className="chat-screen__composer">
        <textarea
          rows={1}
          value={draft}
          placeholder="Что ты делаешь?"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        {sending ? (
          <button className="chat-screen__send chat-screen__send--stop" onClick={handleStop} aria-label="Остановить">
            ■
          </button>
        ) : (
          <button className="chat-screen__send" onClick={send} disabled={!draft.trim()} aria-label="Отправить">
            ↑
          </button>
        )}
      </div>
    </div>
  );
}
