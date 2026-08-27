import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader, PrimaryButton, Spinner } from "../components/Common";
import "./FormScreen.css";

export default function WorldFormScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [form, setForm] = useState({ name: "", description: "", image_path: null });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [genError, setGenError] = useState(null);

  useEffect(() => {
    if (isEdit) {
      api.getWorld(id).then((w) => {
        setForm({ name: w.name, description: w.description, image_path: w.image_path || null });
        setLoading(false);
      });
    }
  }, [id, isEdit]);

  const canSave = form.name.trim() && form.description.trim();
  const canGenerateImage = form.name.trim() && form.description.trim() && !generatingImage;

  const handleGenerateImage = async () => {
    if (!canGenerateImage) return;
    setGeneratingImage(true);
    setGenError(null);
    try {
      const res = await api.generateWorldImage({ name: form.name, description: form.description });
      setForm((f) => ({ ...f, image_path: res.image_path }));
    } catch (e) {
      setGenError(e.message || "Не удалось сгенерировать изображение");
    } finally {
      setGeneratingImage(false);
    }
  };

  const handleSave = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      if (isEdit) {
        await api.updateWorld(id, form);
        navigate(`/worlds/${id}`, { replace: true });
      } else {
        const created = await api.createWorld(form);
        navigate(`/worlds/${created.id}`, { replace: true });
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="screen form-screen">
      <ScreenHeader title={isEdit ? "Изменить мир" : "Новый мир"} />

      <div className="world-form__image" onClick={handleGenerateImage}>
        {form.image_path ? (
          <img src={`/uploads/${form.image_path}`} alt="" />
        ) : (
          <div className="world-form__image-placeholder">◈</div>
        )}
        <div className="world-form__image-overlay">
          {generatingImage ? "Рисуем…" : form.image_path ? "✦ Перегенерировать" : "✦ Сгенерировать изображение"}
        </div>
      </div>
      {!form.description.trim() && <p className="form-screen__hint" style={{ padding: "0 18px" }}>Сначала заполни описание ниже</p>}
      {genError && <p className="form-screen__error" style={{ padding: "0 18px" }}>{genError}</p>}

      <label className="form-field">
        <span>Название</span>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="Например, Сомниум"
          maxLength={80}
        />
      </label>

      <label className="form-field">
        <span>Описание мира</span>
        <textarea
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          rows={10}
          placeholder="Правила мира, атмосфера, конфликты — это станет частью системного промпта для персонажей внутри мира."
          maxLength={4000}
        />
      </label>

      <div style={{ marginTop: 8 }}>
        <PrimaryButton onClick={handleSave} disabled={!canSave} loading={saving}>
          {isEdit ? "Сохранить" : "Создать мир"}
        </PrimaryButton>
      </div>
    </div>
  );
}
