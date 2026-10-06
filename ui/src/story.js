import { create } from "zustand";
import { useEnv, useDesk, appForAction } from "./store";

// Story mode: after each step, act it out in turn. First the tutor's action (its window comes to the
// front), then what the tracker saw the student do while that time passed, then anything the student said.
// View state only: everything shown comes from the step's entry in the payload's action_log.
// Captions say what the tracker saw ("Feed in front, 5 min"), never what the student thought.
export const useStory = create(() => ({ beat: null }));   // { actor: "tutor"|"student", app, text, away }

const INTENT = { explain: "explains", hint: "gives a hint", give_answer: "gives the answer", nudge: "nudges", other: "messages" };
const clip = (s, n = 90) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");

function tutorText(e) {
  const a = e.args || {};
  switch (e.action) {
    case "messages_send_to_student": return `${INTENT[a.intent] || "messages"}: “${clip(a.text, 80)}”`;
    case "messages_read_channel": return `reads ${a.channel}`;
    case "reader_open_section": return `opens “${a.section}” for the student to read`;
    case "reader_peek_section": return `reads “${a.section}” for itself`;
    case "quiz_run": return `gives a ${a.n_items || 3}-question quiz on ${a.concept} · ${clip(e.output.split("\n")[0], 40)}`;
    case "feed_scroll": return "checks the student's feed";
    case "feed_mute": return `mutes ${a.source} on the feed`;
    case "feed_unmute": return `unmutes ${a.source}`;
    case "calendar_list": return "checks the calendar";
    case "calendar_add_block": return `adds “${a.title}” to the calendar`;
    case "notes_list": return "looks at the student's notes";
    case "notes_read": return `reads the note “${a.note_id}”`;
    case "notes_append": return `adds to the note “${a.note_id}”`;
    case "files_ls": case "files_search": case "files_outline": return `looks through files${a.path ? " in " + a.path : a.query ? " for “" + a.query + "”" : ""}`;
    case "browser_visit": return `opens ${a.url}`;
    case "session_wait": return `waits ${a.minutes} min`;
    case "session_end": return `ends the session${a.summary ? ": “" + clip(a.summary, 70) + "”" : ""}`;
    default: return e.action.replace(/_/g, " ");
  }
}

const SEEN = { reader: "Reader in front", messages: "Messages in front", quiz: "Quiz in front", feed: "Feed in front", notes: "Notes in front" };

function beatsFor(e) {
  const out = [{ actor: "tutor", app: appForAction(e.action), text: tutorText(e), ms: 1600 }];
  for (const a of e.activity || []) {
    if (a.app === "idle") out.push({ actor: "student", app: null, away: true, text: `away from the screen, ${a.minutes} min (resting, or on their phone: the tracker can't tell)`, ms: 1100 });
    else out.push({ actor: "student", app: a.app, text: `${SEEN[a.app] || a.app}, ${a.minutes} min`, ms: 1000 });
  }
  for (const t of e.student_said || []) out.push({ actor: "student", app: "messages", text: `says: “${clip(t, 80)}”`, ms: 1800 });
  return out;
}

let queue = [], lastStep = 0, lastEpisode = null, timer = null;

function play() {
  if (timer) return;
  const next = () => {
    const b = queue.shift();
    if (!b || !useDesk.getState().story) { queue = []; timer = null; useStory.setState({ beat: null }); return; }
    if (b.app) useDesk.getState().open(b.app);
    useStory.setState({ beat: b });
    const fast = queue.length > 8 ? 0.35 : queue.length > 3 ? 0.7 : 1;     // catch up if steps arrive faster than beats
    timer = setTimeout(next, b.ms * fast);
  };
  next();
}

export function startStory() {
  useEnv.subscribe((s) => {
    const p = s.payload;
    if (!p) return;
    const log = p.action_log || [];
    if (p.episode_id !== lastEpisode) {                                         // new episode
      lastEpisode = p.episode_id;
      queue = []; lastStep = 0; useStory.setState({ beat: null });
    }
    if (!useDesk.getState().story) { lastStep = p.step; return; }
    const fresh = log.filter((e) => e.step > lastStep);
    if (!fresh.length) return;
    lastStep = fresh[fresh.length - 1].step;
    for (const e of fresh) queue.push(...beatsFor(e));
    play();
  });
}
