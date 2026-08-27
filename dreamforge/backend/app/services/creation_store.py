"""
Сессии режима "создать вместе с ИИ" — это черновик обсуждения, а не финальные данные,
поэтому намеренно не лежат в data.json рядом с персонажами и мирами. Живут в памяти
процесса, пока пользователь не нажмёт "Готово" (тогда превращаются в настоящего
персонажа/мир через store) или не отменит/не забудет (тогда просто исчезнут при
перезапуске сервера — и это нормально для черновика).
"""
import uuid

_sessions: dict[str, dict] = {}


def create_session(kind: str, world_id: str | None) -> dict:
    session = {
        "id": f"creation_{uuid.uuid4().hex[:10]}",
        "kind": kind,
        "world_id": world_id,
        "history": [],
    }
    _sessions[session["id"]] = session
    return session


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def append_message(session_id: str, role: str, content: str) -> None:
    session = _sessions.get(session_id)
    if session:
        session["history"].append({"role": role, "content": content})


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
