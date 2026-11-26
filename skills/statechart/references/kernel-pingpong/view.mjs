const w = (v, i) => ({ load: "next tile", writing: "writing LDS", barrier: "at barrier", reading: "reading LDS" })[v.pc[i]];
export const title = "2 waves, 1 s_barrier per K step";
export const state = (v) => ({ "Wave 1": w(v, 1), "Wave 2": w(v, 2) });
export const step = (action) =>
  ({ StartWrite: "a wave starts its global to LDS copy", EndWrite: "the copy lands", Barrier: "both waves pass s_barrier",
     EndRead: "the wave finishes its MFMAs", Done: "the K loop ends" })[action] ?? action;
