import { useWorkspace, Empty } from "./common";
import { clock } from "../time";

export default function Quiz() {
  const ws = useWorkspace();
  if (!ws) return <Empty>No episode.</Empty>;
  if (!ws.quiz_log.length) return <Empty>No quizzes yet. The agent runs these with quiz_run.</Empty>;
  return (
    <table className="table">
      <thead>
        <tr><th>When</th><th>Concept</th><th>Score</th><th>Difficulty</th><th></th></tr>
      </thead>
      <tbody>
        {ws.quiz_log.map((q, i) => (
          <tr key={i}>
            <td>{clock(q.t)}</td>
            <td><code>{q.concept}</code></td>
            <td>
              <div className="bar"><div style={{ width: `${(100 * q.correct) / q.n}%` }} /></div>
              {q.correct}/{q.n}
            </td>
            <td>{q.difficulty.toFixed(1)}</td>
            <td>{q.aided && <span className="badge warn" title="Help was given on this concept this session">aided</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
