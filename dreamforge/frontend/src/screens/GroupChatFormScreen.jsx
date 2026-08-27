import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader, PrimaryButton, Spinner, EmptyState } from "../components/Common";
import DreamAvatar from "../components/DreamAvatar";
import "./FormScreen.css";
import "./GroupChatFormScreen.css";

const MAX_MEMBERS = 6;

export default function GroupChatFormScreen() {
  const navigate = useNavigate();
  const [characters, setCharacters] = useState(null);
  const [selected, setSelected] = useState([]);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listCharacters().then(setCharacters);
  }, []);

  const toggle = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_MEMBERS) return prev;
      return [...prev, id];
    });
  };

  const canSave = name.trim() && selected.length >= 2;

  const handleSave = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      const chat = await api.createGroupChat({ name: name.trim(), character_ids: selected });
      navigate(`/group/${chat.id}`, { replace: true });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="screen form-screen">
      <ScreenHeader title="Новый групповой чат" />

      <label className="form-field">
        <span>Название разговора</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Например, Вечер в таверне" maxLength={80} />
      </label>

      <div className="form-field">
        <span>Участники (минимум 2, максимум {MAX_MEMBERS})</span>
      </div>

      {characters === null ? (
        <Spinner />
      ) : characters.length < 2 ? (
        <EmptyState icon="✦" title="Нужно минимум 2 персонажа" description="Сначала создай ещё персонажей во вкладке «Персонажи»." />
      ) : (
        <div className="group-picker">
          {characters.map((c) => {
            const isSelected = selected.includes(c.id);
            return (
              <button key={c.id} className={"group-picker__item" + (isSelected ? " is-selected" : "")} onClick={() => toggle(c.id)}>
                <DreamAvatar src={c.avatar_path ? `/uploads/${c.avatar_path}` : null} name={c.name} size={46} glow={isSelected} />
                <span>{c.name}</span>
                {isSelected && <span className="group-picker__check">✓</span>}
              </button>
            );
          })}
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        <PrimaryButton onClick={handleSave} disabled={!canSave} loading={saving}>
          Создать разговор
        </PrimaryButton>
      </div>
    </div>
  );
}
