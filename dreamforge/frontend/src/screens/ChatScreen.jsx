import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamChatMessage, streamEditMessage, streamRegenerate } from "../api/client";
import DreamAvatar from "../components/DreamAvatar";
import MessageText from "../components/MessageText";
import { formatMessageTime } from "../utils/time";
import TypingIndicator from "../components/TypingIndicator";
import MessageActionSheet from "../components/MessageActionSheet";
import { Spinner } from "../components/Common";
import { useLongPress } from "../utils/useLongPress";
import { hapticImpact, hapticNotify } from "../utils/haptics";
import "./ChatScreen.css";

export default function ChatScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [messages, setMessages] = useState(null); // [{role, content, image?}]
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [editingActive, setEditingActive] = useState(false);
  const [actionSheetTarget, setActionSheetTarget] = useState(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getCharacter(id), api.getChatHistory(id)]).then(([c, history]) => {
      if (!alive) return;
      setCharacter(c);
      setMessages(history);
    });
    return () => {
      alive = false;
    };
  }, [id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingText]);

  const busy = sending || regenerating;

  const resyncFromServer = async () => {
    const history = await api.getChatHistory(id);
    setMessages(history);
  };

  const send = async () => {
    const content = draft.trim();
    if (!content || busy) return;
    hapticImpact("light");

    if (editingActive) {
      setEditingActive(false);
      setDraft("");
      setMessages((prev) => [...prev.slice(0, -1), { role: "user", content }]);
      setSending(true);
      setStreamingText("");
      const controller = new AbortController();
      abortRef.current = controller;
      await streamEditMessage(
        id,
        content,
        {
          onChunk: (text) => setStreamingText((prev) => prev + text),
          onDone: ({ text, image }) => {
            setMessages((prev) => [...prev, { role: "assistant", content: text, image }]);
            setStreamingText(null);
            setSending(false);
            hapticNotify("success");
          },
          onError: (message) => {
            setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}`, isError: true }]);
            setStreamingText(null);
            setSending(false);
            hapticNotify("error");
          },
          onAbort: async () => {
            setStreamingText(null);
            setSending(false);
            await resyncFromServer();
          },
        },
        controller.signal
      );
      return;
    }

    setDraft("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content }]);
    setStreamingText("");
    const controller = new AbortController();
    abortRef.current = controller;

    await streamChatMessage(
      id,
      content,
      {
        onChunk: (text) => setStreamingText((prev) => prev + text),
        onDone: ({ text, image }) => {
          setMessages((prev) => [...prev, { role: "assistant", content: text, image }]);
          setStreamingText(null);
          setSending(false);
          hapticNotify("success");
        },
        onError: (message) => {
          setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}`, isError: true }]);
          setStreamingText(null);
          setSending(false);
          hapticNotify("error");
        },
        onAbort: async () => {
          // Бэкенд по возможности сохранил то, что успел написать персонаж — синхронизируемся с ним,
          // а не выдумываем сами, что там оборвалось.
          setStreamingText(null);
          setSending(false);
          await resyncFromServer();
        },
      },
      controller.signal
    );
  };

  const handleStop = () => {
    hapticImpact("medium");
    abortRef.current?.abort();
  };

  const handleRegenerate = async () => {
    if (busy || messages.length === 0) return;
    hapticImpact("medium");
    setRegenerating(true);
    setMessages((prev) => prev.slice(0, -1));
    setStreamingText("");
    const controller = new AbortController();
    abortRef.current = controller;

    await streamRegenerate(
      id,
      {
        onChunk: (text) => setStreamingText((prev) => prev + text),
        onDone: ({ text, image }) => {
          setMessages((prev) => [...prev, { role: "assistant", content: text, image }]);
          setStreamingText(null);
          setRegenerating(false);
          hapticNotify("success");
        },
        onError: (message) => {
          setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}`, isError: true }]);
          setStreamingText(null);
          setRegenerating(false);
          hapticNotify("error");
        },
        onAbort: async () => {
          setStreamingText(null);
          setRegenerating(false);
          await resyncFromServer();
        },
      },
      controller.signal
    );
  };

  const handleEditRequest = (content) => {
    setEditingActive(true);
    setMessages((prev) => prev.slice(0, -1)); // визуально убираем старый ответ, пока правим своё сообщение
    setDraft(content);
  };

  const cancelEdit = () => {
    setEditingActive(false);
    setDraft("");
    resyncFromServer();
  };

  const handleClear = async () => {
    setMenuOpen(false);
    hapticImpact("medium");
    await api.clearChat(id);
    await resyncFromServer();
  };

  if (!character || messages === null) return <Spinner />;

  const lastIsAssistant = !busy && messages.length > 0 && messages[messages.length - 1].role === "assistant";

  const openActionSheet = (message, index) => {
    const isUser = message.role === "user";
    const isLast = index === messages.length - 1;
    setActionSheetTarget({
      message,
      isUser,
      canEdit: isUser && isLast && !busy,
      canRegenerate: !isUser && isLast && !busy,
    });
  };

  return (
    <div className="chat-screen">
      <header className="chat-screen__header">
        <button className="chat-screen__back" onClick={() => navigate(-1)} aria-label="Назад">
          ‹
        </button>
        <div className="chat-screen__who" onClick={() => navigate(`/characters/${character.id}`)}>
          <DreamAvatar
            src={character.avatar_path ? `/uploads/${character.avatar_path}` : null}
            name={character.name}
            size={36}
            glow={false}
          />
          <span className="font-display">{character.name}</span>
        </div>
        <button className="chat-screen__menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="Меню">
          ⋯
        </button>
        {menuOpen && (
          <div className="chat-screen__menu">
            <button onClick={handleClear}>Очистить историю</button>
          </div>
        )}
      </header>

      <div className="chat-screen__messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <PressableBubble key={i} message={m} characterName={character.name} onLongPress={() => openActionSheet(m, i)} />
        ))}
        {busy && (streamingText ? (
          <MessageBubble message={{ role: "assistant", content: streamingText }} characterName={character.name} pending />
        ) : (
          <div className="bubble-row">
            <TypingIndicator name={character.name} />
          </div>
        ))}
        {lastIsAssistant && (
          <div className="chat-screen__regenerate-row">
            <button className="chat-screen__regenerate-btn" onClick={handleRegenerate}>
              ↻ Перегенерировать
            </button>
          </div>
        )}
      </div>

      {editingActive && (
        <div className="chat-screen__edit-banner">
          <span>✎ Редактируешь своё сообщение</span>
          <button onClick={cancelEdit}>Отмена</button>
        </div>
      )}

      <div className="chat-screen__composer">
        <textarea
          rows={1}
          value={draft}
          placeholder={editingActive ? "Исправь сообщение..." : `Напиши ${character.name}...`}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        {busy ? (
          <button className="chat-screen__send chat-screen__send--stop" onClick={handleStop} aria-label="Остановить">
            ■
          </button>
        ) : (
          <button className="chat-screen__send" onClick={send} disabled={!draft.trim()} aria-label="Отправить">
            ↑
          </button>
        )}
      </div>

      <MessageActionSheet
        target={actionSheetTarget}
        onClose={() => setActionSheetTarget(null)}
        onEdit={handleEditRequest}
        onRegenerate={handleRegenerate}
      />
    </div>
  );
}

function PressableBubble({ message, characterName, onLongPress }) {
  const longPressHandlers = useLongPress(onLongPress);
  const isUser = message.role === "user";
  return (
    <div className={"bubble-row" + (isUser ? " bubble-row--user" : "")}>
      <div
        className={"bubble" + (isUser ? " bubble--user" : " bubble--char")}
        {...longPressHandlers}
        style={{ touchAction: "pan-y" }}
      >
        {!isUser && <div className="bubble__name">{characterName}</div>}
        <div className="bubble__text"><MessageText content={message.content} /></div>
        {message.image && <img className="bubble__image" src={`/uploads/${message.image}`} alt="Иллюстрация сцены" />}
        {message.timestamp && <div className="bubble__time">{formatMessageTime(message.timestamp)}</div>}
      </div>
    </div>
  );
}

function MessageBubble({ message, characterName, pending }) {
  const isUser = message.role === "user";
  return (
    <div className={"bubble-row" + (isUser ? " bubble-row--user" : "")}>
      <div className={"bubble" + (isUser ? " bubble--user" : " bubble--char") + (pending ? " bubble--pending" : "")}>
        {!isUser && <div className="bubble__name">{characterName}</div>}
        <div className="bubble__text"><MessageText content={message.content} /></div>
        {message.image && <img className="bubble__image" src={`/uploads/${message.image}`} alt="Иллюстрация сцены" />}
      </div>
    </div>
  );
}
