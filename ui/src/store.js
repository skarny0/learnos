import { create } from "zustand";

// Mirror of the env's websocket payload, 1:1. No logic: whatever the server sends is the state.
// payload = { workspace, step, done, termination, mode, instance_id, level, budget, agent_opened, action_log }
export const useEnv = create(() => ({ connected: false, payload: null }));

let retry = 0;
export function connect() {
  const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
  const ws = new WebSocket(url);
  ws.onopen = () => {
    retry = 0;
    useEnv.setState({ connected: true });
  };
  ws.onmessage = (e) => useEnv.setState({ payload: JSON.parse(e.data) });
  ws.onclose = () => {
    useEnv.setState({ connected: false });
    setTimeout(connect, Math.min(5000, 500 * 2 ** retry++));
  };
}

// Live mode only: the human is the learner, so the desktop reports what they are looking at.
// Same ActivityEvent schema the simulator streams (env/learnos_env/state.py).
export function reportActivity(app, detail = "") {
  const p = useEnv.getState().payload;
  if (!p || p.mode !== "live") return;
  fetch("/api/live/activity", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ t: p.workspace.t, app, minutes: 0, detail }),
  }).catch(() => {});
}

// ---------------------------------------------------------------- desktop --
// Window layout is view state only (positions, z-order). It never feeds back into the env.
export const APPS = [
  { id: "files", title: "Files", icon: "🗂", w: 560, h: 380 },
  { id: "reader", title: "Reader", icon: "📖", w: 560, h: 440 },
  { id: "notes", title: "Notes", icon: "📝", w: 520, h: 420 },
  { id: "calendar", title: "Calendar", icon: "📅", w: 640, h: 460 },
  { id: "messages", title: "Messages", icon: "💬", w: 560, h: 420 },
  { id: "quiz", title: "Quiz", icon: "✅", w: 420, h: 340 },
  { id: "browser", title: "Browser", icon: "🌐", w: 540, h: 380 },
  { id: "feed", title: "Feed", icon: "📱", w: 400, h: 500 },
  { id: "activity", title: "Activity Monitor", icon: "📈", w: 620, h: 300, system: true },
  { id: "agent", title: "Agent Log", icon: "🤖", w: 520, h: 420, system: true },
];

// which window an agent action belongs to (tool names are "{app}_{action}")
export function appForAction(action) {
  const app = (action || "").split("_")[0];
  if (app === "session") return "activity";
  return APPS.some((a) => a.id === app) ? app : "agent";
}

// Default placement: Agent Log owns the right column, Activity Monitor the bottom strip,
// learning apps cascade in the space left over.
function home(a, n) {
  const W = window.innerWidth, H = window.innerHeight;
  const logW = Math.min(460, W * 0.32);
  if (a.id === "agent") return { x: W - logW - 12, y: 34, w: logW, h: H - 150 };
  if (a.id === "activity") return { x: 12, y: H - 290, w: Math.min(620, W - logW - 40), h: 190 };
  const k = n % 6;
  const w = Math.min(a.w, W - logW - 60), h = Math.min(a.h, H - 340);
  return { x: 24 + k * 34, y: 38 + k * 26, w, h };
}

let z = 10;
export const useDesk = create((set, get) => ({
  wins: {},            // id -> { x, y, w, h, z, min }
  focused: null,
  follow: true,        // auto-open the window the agent just used
  open(id) {
    const a = APPS.find((x) => x.id === id);
    const cur = get().wins[id];
    const n = Object.keys(get().wins).length;
    const win = cur ? { ...cur, min: false, z: ++z } : { ...home(a, n), z: ++z, min: false };
    set({ wins: { ...get().wins, [id]: win }, focused: id });
    reportActivity(id, "focus");
  },
  close(id) {
    const { [id]: _, ...rest } = get().wins;
    set({ wins: rest, focused: get().focused === id ? null : get().focused });
  },
  minimize(id) {
    set({ wins: { ...get().wins, [id]: { ...get().wins[id], min: true } }, focused: null });
  },
  move(id, patch) {
    set({ wins: { ...get().wins, [id]: { ...get().wins[id], ...patch } } });
  },
  focus(id) {
    if (get().focused === id) return;
    set({ wins: { ...get().wins, [id]: { ...get().wins[id], z: ++z } }, focused: id });
    reportActivity(id, "focus");
  },
  toggleFollow() {
    set({ follow: !get().follow });
  },
}));
