// Тонкая обёртка над window.Telegram.WebApp.HapticFeedback.
// В обычном браузере (дев-режим) API просто нет — все вызовы no-op, ничего не падает.

function tg() {
  return window.Telegram?.WebApp;
}

/** Лёгкая отдача при нажатии/действии. style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' */
export function hapticImpact(style = "light") {
  tg()?.HapticFeedback?.impactOccurred(style);
}

/** Отдача-уведомление о результате. type: 'success' | 'warning' | 'error' */
export function hapticNotify(type = "success") {
  tg()?.HapticFeedback?.notificationOccurred(type);
}

/** Короткий тик при переключении между вариантами (табы, чипы, свитчи). */
export function hapticSelect() {
  tg()?.HapticFeedback?.selectionChanged();
}
