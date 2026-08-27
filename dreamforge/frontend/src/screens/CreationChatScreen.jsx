import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, streamCreationMessage } from "../api/client";
import TypingIndicator from "../components/TypingIndicator";
import MessageText from "../components/MessageText";
import { Spinner } from "../components/Common";
import { hapticImpact, hapticNotify } from "../utils/haptics";
import "./ChatScreen.css";
import "./CreationChatScreen.css";

const TITLES = { world: "Придумываем мир", character: "Придумываем персонажа" };

export default function CreationChatScreen() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeError, setFinalizeError] = useState(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    api.getCreation(id).then(setSession);
  }, [id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [session, streamingText]);

  const send = async () => {
    const content = draft.trim();
    if (!content || sending) return;
    hapticImpact("light");
    setDraft("");
    setSending(true);
    setSession((s) => ({ ...s, history: [...s.history, { role: "user", content }] }));
    setStreamingText("");
    const controller = new AbortController();
    abortRef.current = controller;

    await streamCreationMessage(
      id,
      content,
      {
        onChunk: (text) => setStreamingText((prev) => prev + text),
        onDone: ({ text }) => {
          setSession((s) => ({ ...s, history: [...s.history, { role: "assistant", content: text }] }));
          setStreamingText(null);
          setSending(false);
          hapticNotify("success");
        },
        onError: (message) => {
          setSession((s) => ({ ...s, history: [...s.history, { role: "assistant", content: `⚠️ ${message}` }] }));
          setStreamingText(null);
          setSending(false);
        },
        onAbort: async () => {
          setStreamingText(null);
          setSending(false);
          const fresh = await api.getCreation(id);
          setSession(fresh);
        },
      },
      controller.signal
    );
  };

  const handleStop = () => {
    hapticImpact("medium");
    abortRef.current?.abort();
  };

  const handleCancel = async () => {
    await api.cancelCreation(id).catch(() => {});
    const fallback = params.get("world_id") ? `/worlds/${params.get("world_id")}` : session?.kind === "world" ? "/worlds" : "/characters";
    navigate(fallback, { replace: true });
  };

  const handleFinalize = async () => {
    if (finalizing || sending) return;
    hapticImpact("medium");
    setFinalizing(true);
    setFinalizeError(null);
    try {
      const result = await api.finalizeCreation(id);
      hapticNotify("success");
      if (result.kind === "world") {
        navigate(`/worlds/${result.entity.id}`, { replace: true });
      } else {
        navigate(`/characters/${result.entity.id}`, { replace: true });
      }
    } catch (e) {
      setFinalizeError(e.message || "Не получилось собрать карточку — обсудите чуть подробнее и попробуйте снова");
      hapticNotify("error");
    } finally {
      setFinalizing(false);
    }
  };

  if (!session) return <Spinner />;

  const canFinalize = session.history.some((m) => m.role === "user") && !sending && !finalizing;

  return (
    <div className="chat-screen creation-screen">
      <header className="chat-screen__header creation-screen__header">
        <button className="chat-screen__back" onClick={handleCancel} aria-label="Отменить">
          ‹
        </button>
        <div className="chat-screen__who">
          <span className="font-display">✦ {TITLES[session.kind]}</span>
        </div>
      </header>

      <div className="chat-screen__messages" ref={scrollRef}>
        {session.history.map((m, i) => (
          <div key={i} className={"bubble-row" + (m.role === "user" ? " bubble-row--user" : "")}>
            <div className={"bubble" + (m.role === "user" ? " bubble--user" : " bubble--char")}>
              <div className="bubble__text">
                <MessageText content={m.content} />
              </div>
            </div>
          </div>
        ))}
        {sending &&
          (streamingText ? (
            <div className="bubble-row">
              <div className="bubble bubble--char bubble--pending">
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

      {finalizeError && <div className="creation-screen__error">{finalizeError}</div>}

      <div className="creation-screen__finalize-row">
        <button className="creation-screen__finalize-btn" onClick={handleFinalize} disabled={!canFinalize}>
          {finalizing ? "Собираю карточку…" : "✓ Готово, создать"}
        </button>
      </div>

      <div className="chat-screen__composer">
        <textarea
          rows={1}
          value={draft}
          placeholder="Напиши свою идею..."
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
