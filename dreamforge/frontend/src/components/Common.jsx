import { hapticImpact } from "../utils/haptics";
import "./Common.css";

export function ScreenHeader({ title, action }) {
  return (
    <header className="screen-header">
      <h1 className="screen-header__title font-display">{title}</h1>
      {action}
    </header>
  );
}

export function EmptyState({ icon = "☾", title, description, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">{icon}</div>
      <p className="empty-state__title">{title}</p>
      {description && <p className="empty-state__desc">{description}</p>}
      {action}
    </div>
  );
}

export function IconButton({ children, onClick, label, variant = "default" }) {
  return (
    <button className={`icon-btn icon-btn--${variant}`} onClick={onClick} aria-label={label}>
      {children}
    </button>
  );
}

export function PrimaryButton({ children, onClick, disabled, type = "button", loading }) {
  const handleClick = (e) => {
    if (disabled || loading) return;
    hapticImpact("light");
    onClick?.(e);
  };
  return (
    <button className="btn-primary" onClick={handleClick} disabled={disabled || loading} type={type}>
      {loading ? "…" : children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, danger, type = "button" }) {
  const handleClick = (e) => {
    hapticImpact(danger ? "medium" : "light");
    onClick?.(e);
  };
  return (
    <button className={"btn-secondary" + (danger ? " btn-secondary--danger" : "")} onClick={handleClick} type={type}>
      {children}
    </button>
  );
}

export function Spinner() {
  return <div className="spinner" aria-label="Загрузка" />;
}
