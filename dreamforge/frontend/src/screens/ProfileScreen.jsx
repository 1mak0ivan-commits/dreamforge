import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ScreenHeader, PrimaryButton, Spinner } from "../components/Common";
import "./FormScreen.css";
import "./ProfileScreen.css";

export default function ProfileScreen() {
  const [profile, setProfile] = useState(null);
  const [styleInfo, setStyleInfo] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    api.getProfile().then(setProfile);
    api.getStyle().then(setStyleInfo);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateProfile(profile);
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1600);
    } finally {
      setSaving(false);
    }
  };

  const chooseStyle = async (key) => {
    setStyleInfo((s) => ({ ...s, current: key }));
    await api.setStyle(key);
  };

  if (!profile || !styleInfo) return <Spinner />;

  return (
    <div className="screen form-screen">
      <ScreenHeader title="Профиль" />

      <label className="form-field">
        <span>Ваше имя</span>
        <input value={profile.name} onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} maxLength={60} />
      </label>
      <label className="form-field">
        <span>Ваш характер</span>
        <input
          value={profile.personality}
          onChange={(e) => setProfile((p) => ({ ...p, personality: e.target.value }))}
          placeholder="Как вас видят персонажи"
          maxLength={300}
        />
      </label>
      <label className="form-field">
        <span>О себе</span>
        <textarea
          value={profile.description}
          onChange={(e) => setProfile((p) => ({ ...p, description: e.target.value }))}
          rows={4}
          maxLength={1000}
        />
      </label>

      <div style={{ marginBottom: 24 }}>
        <PrimaryButton onClick={handleSave} loading={saving}>
          {savedFlash ? "Сохранено ✓" : "Сохранить профиль"}
        </PrimaryButton>
      </div>

      <div className="form-field">
        <span>Стиль иллюстраций</span>
        <div className="style-grid">
          {Object.entries(styleInfo.available).map(([key, info]) => (
            <button
              key={key}
              className={"style-tile" + (styleInfo.current === key ? " is-active" : "")}
              onClick={() => chooseStyle(key)}
            >
              {info.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
