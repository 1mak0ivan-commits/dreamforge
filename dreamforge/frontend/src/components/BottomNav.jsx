import { NavLink } from "react-router-dom";
import { hapticSelect } from "../utils/haptics";
import "./BottomNav.css";

const ICONS = {
  chats: (
    <svg viewBox="0 0 24 24" fill="none">
      <path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  ),
  characters: (
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="3.4" stroke="currentColor" strokeWidth="1.7" />
      <path d="M5 20c1-3.6 4-5.5 7-5.5s6 1.9 7 5.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  worlds: (
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.7" />
      <path d="M4 12h16M12 4c2.4 2.2 3.6 5 3.6 8s-1.2 5.8-3.6 8c-2.4-2.2-3.6-5-3.6-8s1.2-5.8 3.6-8Z" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.4" stroke="currentColor" strokeWidth="1.7" />
      <path d="M12 8v4.4l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
};

const TABS = [
  { to: "/", key: "chats", label: "Чаты", end: true },
  { to: "/characters", key: "characters", label: "Персонажи" },
  { to: "/worlds", key: "worlds", label: "Миры" },
  { to: "/profile", key: "profile", label: "Профиль" },
];

export default function BottomNav() {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => (
        <NavLink
          key={tab.key}
          to={tab.to}
          end={tab.end}
          onClick={hapticSelect}
          className={({ isActive }) => "bottom-nav__item" + (isActive ? " is-active" : "")}
        >
          <span className="bottom-nav__icon">{ICONS[tab.key]}</span>
          <span className="bottom-nav__label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
