import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamGroupMessage } from "../api/client";
import DreamAvatar from "../components/DreamAvatar";
import MessageText from "../components/MessageText";
import { formatMessageTime } from "../utils/time";
import TypingIndicator from "../components/TypingIndicator";
import MessageActionSheet from "../components/MessageActionSheet";
import { Spinner } from "../components/Common";
import { useLongPress } from "../utils/useLongPress";
import { hapticImpact, hapticNotify, hapticSelect } from "../utils/haptics";
import "./ChatScreen.css";
import "./GroupChatScreen.css";

export default function GroupChatScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [chat, setChat] = useState(null); // {name, characters, chat_history}
  const [messages, setMessages] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(null); // {character_id, name, text}
  const [target, setTarget] = useState(null); // null = отвечают все по очереди
  const [menuOpen, setMenuOpen] = useState(false);
  const [actionSheetTarget, setActionSheetTarget] = useState(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  const load = async () => {
    const c = await api.getGroupChat(id);
    setChat(c);
    setMessages(c.chat_history);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  const charById = (cid) => chat?.characters.find((c) => c.id === cid);

  const send = async () => {
    const content = draft.trim();
    if (!content || sending) return;
    hapticImpact("light");
    setDraft("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", character_id: null, content }]);
    const controller = new AbortController();
    abortRef.current = controller;

    await streamGroupMessage(
      id,
      content,
      target,
      {
        onCharStart: ({ character_id, name }) => setStreaming({ character_id, name, text: "" }),
        onChunk: ({ character_id, text }) =>
          setStreaming((prev) => (prev && prev.character_id === character_id ? { ...prev, text: prev.text + text } : prev)),
        onCharDone: ({ character_id, text }) => {
          setMessages((prev) => [...prev, { role: "character", character_id, content: text }]);
          setStreaming(null);
          hapticNotify("success");
        },
        onError: ({ character_id, message }) => {
          setMessages((prev) => [...prev, { role: "character", character_id, content: `⚠️ ${message}`, isError: true }]);
          setStreaming(null);
          hapticNotify("error");
        },
        onDone: () => setSending(false),
        onAbort: async () => {
          setStreaming(null);
          setSending(false);
          const c = await api.getGroupChat(id);
          setChat(c);
          setMessages(c.chat_history);
        },
      },
      controller.signal
    );
    setSending(false);
  };

  const handleStop = () => {
    hapticImpact("medium");
    abortRef.current?.abort();
  };

  const handleClear = async () => {
    setMenuOpen(false);
    hapticImpact("medium");
    await api.clearGroupChat(id);
    load();
  };

  const handleDelete = async () => {
    hapticImpact("heavy");
    await api.deleteGroupChat(id);
    navigate("/", { replace: true });
  };

  if (!chat || messages === null) return <Spinner />;

  const openActionSheet = (message) => {
    setActionSheetTarget({ message, isUser: message.role === "user", canEdit: false, canRegenerate: false });
  };

  return (
    <div className="chat-screen">
      <header className="chat-screen__header">
        <button className="chat-screen__back" onClick={() => navigate(-1)} aria-label="Назад">
          ‹
        </button>
        <div className="chat-screen__who">
          <div className="group-stack">
            {chat.characters.slice(0, 3).map((c) => (
              <DreamAvatar key={c.id} src={c.avatar_path ? `/uploads/${c.avatar_path}` : null} name={c.name} size={30} glow={false} />
            ))}
          </div>
          <span className="font-display">{chat.name}</span>
        </div>
        <button className="chat-screen__menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="Меню">
          ⋯
        </button>
        {menuOpen && (
          <div className="chat-screen__menu">
            <button onClick={handleClear}>Очистить историю</button>
            <button onClick={handleDelete}>Удалить разговор</button>
          </div>
        )}
      </header>

      <div className="chat-screen__messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <PressableGroupBubble
            key={i}
            message={m}
            character={m.character_id ? charById(m.character_id) : null}
            onLongPress={() => openActionSheet(m)}
          />
        ))}
        {streaming &&
          (streaming.text ? (
            <GroupBubble message={{ role: "character", content: streaming.text }} character={{ name: streaming.name }} pending />
          ) : (
            <div className="bubble-row">
              <TypingIndicator name={streaming.name} />
            </div>
          ))}
      </div>

      <div className="group-target-row">
        <button
          className={"group-target-chip" + (target === null ? " is-active" : "")}
          onClick={() => {
            hapticSelect();
            setTarget(null);
          }}
        >
          Все по очереди
        </button>
        {chat.characters.map((c) => (
          <button
            key={c.id}
            className={"group-target-chip" + (target === c.id ? " is-active" : "")}
            onClick={() => {
              hapticSelect();
              setTarget(c.id);
            }}
          >
            {c.name}
          </button>
        ))}
      </div>

      <div className="chat-screen__composer">
        <textarea
          rows={1}
          value={draft}
          placeholder={target ? `Напиши ${charById(target)?.name}...` : "Напиши всем..."}
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

      <MessageActionSheet target={actionSheetTarget} onClose={() => setActionSheetTarget(null)} onEdit={() => {}} onRegenerate={() => {}} />
    </div>
  );
}

function PressableGroupBubble({ message, character, onLongPress }) {
  const longPressHandlers = useLongPress(onLongPress);
  const isUser = message.role === "user";
  return (
    <div className={"bubble-row" + (isUser ? " bubble-row--user" : "")}>
      <div className={"bubble" + (isUser ? " bubble--user" : " bubble--char")} {...longPressHandlers} style={{ touchAction: "pan-y" }}>
        {!isUser && <div className="bubble__name">{character?.name || "?"}</div>}
        <div className="bubble__text"><MessageText content={message.content} /></div>
        {message.timestamp && <div className="bubble__time">{formatMessageTime(message.timestamp)}</div>}
      </div>
    </div>
  );
}

function GroupBubble({ message, character, pending }) {
  const isUser = message.role === "user";
  return (
    <div className={"bubble-row" + (isUser ? " bubble-row--user" : "")}>
      <div className={"bubble" + (isUser ? " bubble--user" : " bubble--char") + (pending ? " bubble--pending" : "")}>
        {!isUser && <div className="bubble__name">{character?.name || "?"}</div>}
        <div className="bubble__text"><MessageText content={message.content} /></div>
      </div>
    </div>
  );
}
