import { describe, expect, it } from "vitest";
import { createHistory, pushHistory, redoHistory, undoHistory } from "./planHistory";

describe("??????? ????????? ?????", () => {
  it("???????????????? ????????? undo ? redo", () => {
    const initial = createHistory({ x: 1 });
    const changed = pushHistory(initial, { x: 2 });
    const undone = undoHistory(changed);
    const redone = redoHistory(undone);

    expect(undone.present).toEqual({ x: 1 });
    expect(redone.present).toEqual({ x: 2 });
    expect(redone.future).toEqual([]);
  });

  it("??????? redo ????? ????? ?????? ? ???????????? ???????", () => {
    let history = createHistory(0);
    history = pushHistory(history, 1, 2);
    history = pushHistory(history, 2, 2);
    history = undoHistory(history);
    history = pushHistory(history, 3, 2);

    expect(history.present).toBe(3);
    expect(history.past).toHaveLength(2);
    expect(history.future).toEqual([]);
  });
});

