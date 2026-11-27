export const title = "A search loop over 3 candidates";
const count = (v, ...s) => Object.values(v.status).filter((x) => s.includes(x)).length;
export const state = (v) =>
  `${count(v, "kept")} kept, ${count(v, "queued", "eligible")} open, ${v.phase}`;
export const step = (action) =>
  ({ Try: "a candidate is measured", Stop: "the loop stops", Done: "the loop has ended" })[action] ?? action;
