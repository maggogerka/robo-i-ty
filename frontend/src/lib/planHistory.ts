export type PlanHistory<T> = {
  past: T[];
  present: T;
  future: T[];
};

export function createHistory<T>(initial: T): PlanHistory<T> {
  return { past: [], present: initial, future: [] };
}

export function pushHistory<T>(
  history: PlanHistory<T>,
  next: T,
  limit = 50,
): PlanHistory<T> {
  return {
    past: [...history.past, history.present].slice(-limit),
    present: next,
    future: [],
  };
}

export function undoHistory<T>(history: PlanHistory<T>): PlanHistory<T> {
  const previous = history.past.at(-1);
  if (previous === undefined) return history;
  return {
    past: history.past.slice(0, -1),
    present: previous,
    future: [history.present, ...history.future],
  };
}

export function redoHistory<T>(history: PlanHistory<T>): PlanHistory<T> {
  const next = history.future[0];
  if (next === undefined) return history;
  return {
    past: [...history.past, history.present],
    present: next,
    future: history.future.slice(1),
  };
}

