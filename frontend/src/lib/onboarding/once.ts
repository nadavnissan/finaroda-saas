// Single-shot transition guard. Pure, dependency-free (unit-tested).
// The first call runs the action; subsequent calls are no-ops until reset().
// Used to make the S5 -> S6 signup transition fire exactly once (no flash / double
// transition), matching the guard pattern used for the scan animation.

export interface Once {
  run(action: () => void): boolean; // returns true only the first time
  done(): boolean;
  reset(): void;
}

export function createOnce(): Once {
  let fired = false;
  return {
    run(action: () => void): boolean {
      if (fired) return false;
      fired = true;
      action();
      return true;
    },
    done: () => fired,
    reset() {
      fired = false;
    },
  };
}
