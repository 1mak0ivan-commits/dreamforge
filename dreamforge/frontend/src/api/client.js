// Единая точка общения с бэкендом. Каждый запрос несёт заголовок с Telegram initData —
// бэкенд им проверяет подлинность пользователя (см. core/telegram_auth.py).

function getInitData() {
  return window.Telegram?.WebApp?.initData || "";
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitData(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка запроса: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- Миры ---
  listWorlds: () => request("/api/worlds"),
  getWorld: (id) => request(`/api/worlds/${id}`),
  createWorld: (data) => request("/api/worlds", { method: "POST", body: JSON.stringify(data) }),
  updateWorld: (id, data) => request(`/api/worlds/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteWorld: (id) => request(`/api/worlds/${id}`, { method: "DELETE" }),
  generateWorldImage: (data) => request("/api/worlds/generate-image", { method: "POST", body: JSON.stringify(data) }),

  // --- Персонажи ---
  listCharacters: () => request("/api/characters"),
  getCharacter: (id) => request(`/api/characters/${id}`),
  createCharacter: (data) => request("/api/characters", { method: "POST", body: JSON.stringify(data) }),
  updateCharacter: (id, data) => request(`/api/characters/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCharacter: (id) => request(`/api/characters/${id}`, { method: "DELETE" }),
  removeCharacterFromWorld: (id) => request(`/api/characters/${id}/remove-from-world`, { method: "POST" }),
  generateAvatar: (data) => request("/api/characters/generate-avatar", { method: "POST", body: JSON.stringify(data) }),

  // --- Чат ---
  getChatHistory: (charId) => request(`/api/chat/${charId}/history`),
  clearChat: (charId) => request(`/api/chat/${charId}/clear`, { method: "POST" }),

  // --- Профиль и стиль ---
  getProfile: () => request("/api/profile"),
  updateProfile: (data) => request("/api/profile", { method: "PUT", body: JSON.stringify(data) }),
  getStyle: () => request("/api/style"),
  setStyle: (style) => request("/api/style", { method: "PUT", body: JSON.stringify({ style }) }),

  // --- Групповые чаты ---
  listGroupChats: () => request("/api/group-chats"),
  getGroupChat: (id) => request(`/api/group-chats/${id}`),
  createGroupChat: (data) => request("/api/group-chats", { method: "POST", body: JSON.stringify(data) }),
  deleteGroupChat: (id) => request(`/api/group-chats/${id}`, { method: "DELETE" }),
  clearGroupChat: (id) => request(`/api/group-chats/${id}/clear`, { method: "POST" }),

  // --- Совместное создание мира/персонажа с ИИ ---
  startCreation: (data) => request("/api/creation/start", { method: "POST", body: JSON.stringify(data) }),
  getCreation: (id) => request(`/api/creation/${id}`),
  cancelCreation: (id) => request(`/api/creation/${id}`, { method: "DELETE" }),
  finalizeCreation: (id) => request(`/api/creation/${id}/finalize`, { method: "POST" }),

  // --- Режим "Войти в мир" (свободное повествование) ---
  startNarrative: (worldId) => request(`/api/worlds/${worldId}/narrative/start`, { method: "POST" }),
  getNarrative: (id) => request(`/api/narratives/${id}`),
  clearNarrative: (id) => request(`/api/narratives/${id}/clear`, { method: "POST" }),

  // --- Медиа ---
  async uploadImage(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/upload-image", {
      method: "POST",
      headers: { "X-Telegram-Init-Data": getInitData() },
      body: form,
    });
    if (!res.ok) throw new Error("Не удалось загрузить изображение");
    return res.json();
  },
};

/**
 * Общий читатель SSE-потока. onEvent(eventName, parsedData) вызывается на каждое событие.
 * Поддерживает signal (AbortController) — при отмене выбрасывается DOMException с name 'AbortError',
 * это отдельно обрабатывают функции-обёртки ниже, чтобы не путать отмену пользователем с реальной ошибкой.
 */
async function _readSSE(res, onEvent) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop(); // последний кусок может быть неполным

    for (const raw of events) {
      if (!raw.trim()) continue;
      const lines = raw.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (!data) continue;
      onEvent(event, JSON.parse(data));
    }
  }
}

async function _postStream(url, body, signal) {
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitData(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
}

/**
 * Отправляет сообщение персонажу и стримит ответ по SSE.
 * onChunk(text) — вызывается на каждый кусочек текста.
 * onDone({ text, image }) — вызывается когда ответ полностью получен.
 * onError(message) — при ошибке.
 * onAbort() — если генерацию остановили через signal (кнопка "Стоп").
 * signal — необязательный AbortController.signal для остановки на лету.
 */
export async function streamChatMessage(charId, content, { onChunk, onDone, onError, onAbort }, signal) {
  let res;
  try {
    res = await _postStream(`/api/chat/${charId}/message`, { content }, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.(e.message);
  }
  if (!res.ok || !res.body) return onError?.(`Ошибка запроса: ${res.status}`);

  try {
    await _readSSE(res, (event, data) => {
      if (event === "chunk") onChunk?.(data.text);
      else if (event === "done") onDone?.(data);
      else if (event === "error") onError?.(data.message);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.(e.message);
  }
}

/**
 * Правит последнее отправленное сообщение пользователя и генерирует новый ответ на него.
 * Тот же набор колбэков, что у streamChatMessage.
 */
export async function streamEditMessage(charId, content, { onChunk, onDone, onError, onAbort }, signal) {
  let res;
  try {
    res = await _postStream(`/api/chat/${charId}/edit-message`, { content }, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.(e.message);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    return onError?.(body.detail || `Ошибка запроса: ${res.status}`);
  }
  try {
    await _readSSE(res, (event, data) => {
      if (event === "chunk") onChunk?.(data.text);
      else if (event === "done") onDone?.(data);
      else if (event === "error") onError?.(data.message);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.(e.message);
  }
}

/**
 * Просит персонажа перегенерировать последний свой ответ.
 */
export async function streamRegenerate(charId, { onChunk, onDone, onError, onAbort }, signal) {
  let res;
  try {
    res = await _postStream(`/api/chat/${charId}/regenerate`, undefined, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.(e.message);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    return onError?.(body.detail || `Ошибка запроса: ${res.status}`);
  }
  try {
    await _readSSE(res, (event, data) => {
      if (event === "chunk") onChunk?.(data.text);
      else if (event === "done") onDone?.(data);
      else if (event === "error") onError?.(data.message);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.(e.message);
  }
}

/**
 * Отправляет сообщение в групповой чат. Может отвечать несколько персонажей по очереди.
 * onCharStart({character_id, name}) — персонаж начал "печатать".
 * onChunk({character_id, text}) — кусочек текста конкретного персонажа.
 * onCharDone({character_id, text}) — персонаж закончил реплику.
 * onDone() — весь ход завершён (все, кто должен был ответить, ответили).
 * onError({character_id, message}) — ошибка генерации у конкретного персонажа.
 * onAbort() — генерацию остановили через signal.
 */
export async function streamGroupMessage(
  chatId,
  content,
  targetCharacterId,
  { onCharStart, onChunk, onCharDone, onDone, onError, onAbort },
  signal
) {
  let res;
  try {
    res = await _postStream(`/api/group-chats/${chatId}/message`, { content, target_character_id: targetCharacterId || null }, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.({ message: e.message });
  }
  if (!res.ok || !res.body) return onError?.({ message: `Ошибка запроса: ${res.status}` });

  try {
    await _readSSE(res, (event, data) => {
      if (event === "char_start") onCharStart?.(data);
      else if (event === "chunk") onChunk?.(data);
      else if (event === "char_done") onCharDone?.(data);
      else if (event === "done") onDone?.();
      else if (event === "error") onError?.(data);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.({ message: e.message });
  }
}

/**
 * Отправляет сообщение в сессию совместного создания мира/персонажа и стримит ответ помощника.
 * Тот же набор колбэков, что у streamChatMessage.
 */
export async function streamCreationMessage(sessionId, content, { onChunk, onDone, onError, onAbort }, signal) {
  let res;
  try {
    res = await _postStream(`/api/creation/${sessionId}/message`, { content }, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.(e.message);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    return onError?.(body.detail || `Ошибка запроса: ${res.status}`);
  }
  try {
    await _readSSE(res, (event, data) => {
      if (event === "chunk") onChunk?.(data.text);
      else if (event === "done") onDone?.(data);
      else if (event === "error") onError?.(data.message);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.(e.message);
  }
}

/**
 * Отправляет действие пользователя в нарратив мира и стримит ответ рассказчика.
 * Тот же набор колбэков, что у streamChatMessage.
 */
export async function streamNarrativeMessage(narrativeId, content, { onChunk, onDone, onError, onAbort }, signal) {
  let res;
  try {
    res = await _postStream(`/api/narratives/${narrativeId}/message`, { content }, signal);
  } catch (e) {
    if (e.name === "AbortError") return onAbort?.();
    return onError?.(e.message);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    return onError?.(body.detail || `Ошибка запроса: ${res.status}`);
  }
  try {
    await _readSSE(res, (event, data) => {
      if (event === "chunk") onChunk?.(data.text);
      else if (event === "done") onDone?.(data);
      else if (event === "error") onError?.(data.message);
    });
  } catch (e) {
    if (e.name === "AbortError") onAbort?.();
    else onError?.(e.message);
  }
}
