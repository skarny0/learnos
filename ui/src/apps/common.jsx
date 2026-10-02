import { marked } from "marked";
import { useEnv } from "../store";

// Agent-written text (notes_append, messages) is untrusted: escape raw HTML before rendering markdown.
export function Markdown({ text }) {
  const html = marked.parse((text || "").replace(/</g, "&lt;"), { gfm: true, breaks: true });
  return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />;
}

export const useWorkspace = () => useEnv((s) => s.payload?.workspace);
export const usePayload = () => useEnv((s) => s.payload);

// Most recent agent action on a given app, e.g. lastAction(log, "reader") -> {action, args, ...}
export function lastAction(log, app) {
  for (let i = (log || []).length - 1; i >= 0; i--) if (log[i].action.startsWith(app + "_")) return log[i];
  return null;
}

// Slice a markdown file to one section (heading line up to the next heading).
export function sliceSection(md, section) {
  const lines = (md || "").split("\n");
  const start = lines.findIndex((l) => l.startsWith("#") && l.replace(/^#+\s*/, "").trim() === section);
  if (start < 0) return md;
  let end = lines.findIndex((l, i) => i > start && l.startsWith("#"));
  if (end < 0) end = lines.length;
  return lines.slice(start, end).join("\n");
}

export const Empty = ({ children }) => <div className="empty">{children}</div>;

export function AgentBadge({ children = "agent" }) {
  return <span className="badge agent">🤖 {children}</span>;
}
