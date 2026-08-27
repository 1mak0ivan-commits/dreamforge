import "./Skeleton.css";

function Block({ className = "", style }) {
  return <div className={"skeleton " + className} style={style} />;
}

/** Заглушка для списка чатов: несколько строк "аватар + две строки текста". */
export function SkeletonChatList({ count = 4 }) {
  return (
    <div className="skeleton-list">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-list__row" key={i}>
          <Block className="skeleton--circle" style={{ width: 54, height: 54 }} />
          <div className="skeleton-list__lines">
            <Block style={{ width: "45%", height: 14 }} />
            <Block style={{ width: "75%", height: 12 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Заглушка для сетки карточек персонажей/миров. */
export function SkeletonCardGrid({ count = 4 }) {
  return (
    <div className="card-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <Block className="skeleton-card__image" />
          <div className="skeleton-card__body">
            <Block style={{ width: "70%", height: 14 }} />
            <Block style={{ width: "95%", height: 11 }} />
            <Block style={{ width: "60%", height: 11 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Заглушка для экрана деталей персонажа/мира: аватар по центру + строки текста. */
export function SkeletonHero() {
  return (
    <div className="skeleton-hero">
      <Block className="skeleton--circle" style={{ width: 128, height: 128 }} />
      <Block style={{ width: 160, height: 20, marginTop: 14 }} />
      <Block style={{ width: 110, height: 13, marginTop: 8 }} />
      <div className="skeleton-hero__desc">
        <Block style={{ width: "100%", height: 12 }} />
        <Block style={{ width: "100%", height: 12 }} />
        <Block style={{ width: "70%", height: 12 }} />
      </div>
    </div>
  );
}
