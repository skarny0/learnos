import { useRef } from "react";
import { useDesk } from "./store";

// System-7-style window: striped title bar (drag), close box, collapse box, resize corner.
export default function Window({ id, title, children }) {
  const win = useDesk((s) => s.wins[id]);
  const focused = useDesk((s) => s.focused === id);
  const { focus, close, minimize, move } = useDesk.getState();
  const drag = useRef(null);

  if (!win || win.min) return null;

  const startDrag = (e, kind) => {
    e.preventDefault();
    e.stopPropagation();
    focus(id);
    drag.current = { kind, sx: e.clientX, sy: e.clientY, ...win };
    const onMove = (ev) => {
      const d = drag.current;
      const dx = ev.clientX - d.sx, dy = ev.clientY - d.sy;
      if (d.kind === "move") move(id, { x: Math.max(-d.w + 80, d.x + dx), y: Math.max(22, d.y + dy) });
      else move(id, { w: Math.max(260, d.w + dx), h: Math.max(160, d.h + dy) });
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <div
      className={"win" + (focused ? " focused" : "")}
      style={{ left: win.x, top: win.y, width: win.w, height: win.h, zIndex: win.z }}
      onPointerDown={() => focus(id)}
    >
      <div className="titlebar" onPointerDown={(e) => startDrag(e, "move")}>
        <button className="box close" title="Close" onPointerDown={(e) => e.stopPropagation()} onClick={() => close(id)} />
        <span className="title">{title}</span>
        <button className="box collapse" title="Minimize" onPointerDown={(e) => e.stopPropagation()} onClick={() => minimize(id)} />
      </div>
      <div className="body">{children}</div>
      <div className="grow" onPointerDown={(e) => startDrag(e, "resize")} />
    </div>
  );
}
