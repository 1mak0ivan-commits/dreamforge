import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader, PrimaryButton, Spinner } from "../components/Common";
import DreamAvatar from "../components/DreamAvatar";
import "./FormScreen.css";

const empty = { name: "", personality: "", description: "", greeting: "", world_id: null, avatar_path: null, visual_identity: null };

export default function CharacterFormScreen() {
  const { id } = useParams(); // есть — режим редактирования
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [form, setForm] = useState(empty);
  const [worlds, setWorlds] = useState([]);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [generatingAvatar, setGeneratingAvatar] = useState(false);
  const [genError, setGenError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.listWorlds().then(setWorlds);
    if (isEdit) {
      api.getCharacter(id).then((c) => {
        setForm({
          name: c.name,
          personality: c.personality,
          description: c.description,
          greeting: c.greeting,
          world_id: c.world_id,
          avatar_path: c.avatar_path,
          visual_identity: c.visual_identity || null,
        });
        setLoading(false);
      });
    } else {
      const worldFromQuery = params.get("world_id");
      if (worldFromQuery) setForm((f) => ({ ...f, world_id: worldFromQuery }));
    }
  }, [id, isEdit, params]);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const canSave = form.name.trim() && form.personality.trim() && form.description.trim() && form.greeting.trim();
  const canGenerateAvatar = form.name.trim() && form.description.trim() && !generatingAvatar;

  const handleGenerateAvatar = async () => {
    if (!canGenerateAvatar) return;
    setGeneratingAvatar(true);
    setGenError(null);
    try {
      const res = await api.generateAvatar({
        name: form.name,
        personality: form.personality,
        description: form.description,
      });
      setAvatarFile(null);
      setAvatarPreview(null);
      setForm((f) => ({ ...f, avatar_path: res.avatar_path, visual_identity: res.visual_identity }));
    } catch (e) {
      setGenError(e.message || "Не удалось сгенерировать портрет");
    } finally {
      setGeneratingAvatar(false);
    }
  };

  const handleSave = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      let avatar_path = form.avatar_path;
      if (avatarFile) {
        const res = await api.uploadImage(avatarFile);
        avatar_path = res.filename;
      }
      const payload = { ...form, avatar_path, world_id: form.world_id || null };
      if (isEdit) {
        await api.updateCharacter(id, payload);
        navigate(`/characters/${id}`, { replace: true });
      } else {
        const created = await api.createCharacter(payload);
        navigate(`/characters/${created.id}`, { replace: true });
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="screen form-screen">
      <ScreenHeader title={isEdit ? "Изменить персонажа" : "Новый персонаж"} />

      <div className="form-screen__avatar" onClick={() => fileInputRef.current?.click()}>
        <DreamAvatar
          src={avatarPreview || (form.avatar_path ? `/uploads/${form.avatar_path}` : null)}
          name={form.name || "?"}
          size={96}
        />
        <span>Загрузить портрет</span>
        <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={handleFileChange} />
      </div>

      <div className="form-screen__generate-avatar">
        <button
          type="button"
          className="form-screen__generate-btn"
          onClick={handleGenerateAvatar}
          disabled={!canGenerateAvatar}
        >
          {generatingAvatar ? "Рисуем портрет…" : "✦ Сгенерировать портрет по описанию"}
        </button>
        {!form.description.trim() && <p className="form-screen__hint">Сначала заполни описание ниже</p>}
        {genError && <p className="form-screen__error">{genError}</p>}
        {form.visual_identity && !generatingAvatar && (
          <p className="form-screen__hint">
            Внешность закреплена — будущие иллюстрации сцен будут рисовать персонажа похожим.
          </p>
        )}
      </div>

      <label className="form-field">
        <span>Имя</span>
        <input value={form.name} onChange={update("name")} placeholder="Например, Анна" maxLength={60} />
      </label>

      <label className="form-field">
        <span>Характер</span>
        <input value={form.personality} onChange={update("personality")} placeholder="Например, добрая, но замкнутая" maxLength={500} />
      </label>

      <label className="form-field">
        <span>Описание</span>
        <textarea value={form.description} onChange={update("description")} rows={5} placeholder="Подробное описание внешности, истории, манеры речи..." maxLength={4000} />
      </label>

      <label className="form-field">
        <span>Первая реплика</span>
        <textarea value={form.greeting} onChange={update("greeting")} rows={2} placeholder="Что персонаж скажет первым при начале чата" maxLength={1000} />
      </label>

      <label className="form-field">
        <span>Мир (необязательно)</span>
        <select value={form.world_id || ""} onChange={(e) => setForm((f) => ({ ...f, world_id: e.target.value || null }))}>
          <option value="">Без мира</option>
          {worlds.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </label>

      <div style={{ marginTop: 8 }}>
        <PrimaryButton onClick={handleSave} disabled={!canSave} loading={saving}>
          {isEdit ? "Сохранить" : "Создать персонажа"}
        </PrimaryButton>
      </div>
    </div>
  );
}
