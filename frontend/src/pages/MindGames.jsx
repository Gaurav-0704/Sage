import React, { useState, useEffect, useRef } from "react";

const GAMES = [
  { id: "match", icon: "🃏", title: "Memory Match",   sub: "Find all the pairs" },
  { id: "math",  icon: "➕", title: "Quick Math",     sub: "30-second arithmetic blitz" },
  { id: "react", icon: "⚡", title: "Reaction Time",  sub: "Tap when it turns green" },
];

export default function MindGames() {
  const [game, setGame] = useState(null);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Mind Games</h1>
          <p className="page-sub">Quick games to keep your brain sharp.</p>
        </div>
      </div>

      {!game ? (
        <div className="grid grid-cols-3">
          {GAMES.map((g) => (
            <button key={g.id} className="game-card" onClick={() => setGame(g.id)}>
              <div className="icon">{g.icon}</div>
              <div className="title">{g.title}</div>
              <div className="sub">{g.sub}</div>
            </button>
          ))}
        </div>
      ) : (
        <div>
          <button className="btn btn-secondary mb-16"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                  onClick={() => setGame(null)}>
            ← Back to games
          </button>
          {game === "match" && <MemoryMatch/>}
          {game === "math"  && <QuickMath/>}
          {game === "react" && <ReactionTime/>}
        </div>
      )}
    </div>
  );
}

/* ---------- Memory Match ---------- */
function MemoryMatch() {
  const ICONS = ["🐶", "🐱", "🦊", "🐼", "🦁", "🐸", "🐵", "🐧"];
  const [cards, setCards] = useState(() => shuffle());
  const [flipped, setFlipped] = useState([]);
  const [matched, setMatched] = useState(new Set());
  const [moves, setMoves] = useState(0);
  const [start] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(t);
  }, [start]);

  function shuffle() {
    const arr = [...ICONS, ...ICONS]
      .map((v, i) => ({ id: i, v, key: Math.random() }))
      .sort((a, b) => a.key - b.key);
    return arr;
  }

  const flip = (i) => {
    if (matched.has(i) || flipped.includes(i) || flipped.length === 2) return;
    const next = [...flipped, i];
    setFlipped(next);
    if (next.length === 2) {
      setMoves((m) => m + 1);
      const [a, b] = next;
      if (cards[a].v === cards[b].v) {
        setTimeout(() => {
          setMatched(new Set([...matched, a, b]));
          setFlipped([]);
        }, 350);
      } else {
        setTimeout(() => setFlipped([]), 700);
      }
    }
  };

  const won = matched.size === cards.length;
  const reset = () => {
    setCards(shuffle()); setFlipped([]); setMatched(new Set());
    setMoves(0); setElapsed(0);
  };

  return (
    <div className="card">
      <div className="card-title">
        Memory Match
        <span className="text-3" style={{ fontWeight: 500 }}>
          {moves} moves · {elapsed}s
        </span>
      </div>
      {won && (
        <div className="success-banner">
          🎉 You won in {moves} moves and {elapsed}s.{" "}
          <button className="btn btn-secondary" style={{ marginLeft: 8, padding: "4px 10px", fontSize: 12 }}
                  onClick={reset}>Play again</button>
        </div>
      )}
      <div className="match-grid">
        {cards.map((c, i) => {
          const show = flipped.includes(i) || matched.has(i);
          return (
            <button key={i}
                    className={"match-tile " +
                                (show ? (matched.has(i) ? "matched" : "flipped") : "")}
                    onClick={() => flip(i)}>
              {show ? c.v : "?"}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- Quick Math ---------- */
function QuickMath() {
  const [problem, setProblem] = useState(() => gen());
  const [answer, setAnswer] = useState("");
  const [score, setScore] = useState(0);
  const [time, setTime] = useState(30);
  const [running, setRunning] = useState(false);

  function gen() {
    const ops = ["+", "-", "×"];
    const op = ops[Math.floor(Math.random() * 3)];
    let a = Math.floor(Math.random() * 20) + 1;
    let b = Math.floor(Math.random() * 20) + 1;
    if (op === "-" && b > a) [a, b] = [b, a];
    if (op === "×") { a = Math.floor(Math.random() * 12) + 2; b = Math.floor(Math.random() * 12) + 2; }
    const v = op === "+" ? a + b : op === "-" ? a - b : a * b;
    return { a, b, op, v };
  }

  useEffect(() => {
    if (!running) return;
    if (time === 0) { setRunning(false); return; }
    const t = setTimeout(() => setTime((t) => t - 1), 1000);
    return () => clearTimeout(t);
  }, [running, time]);

  const start = () => {
    setScore(0); setTime(30); setProblem(gen()); setAnswer(""); setRunning(true);
  };

  const submit = (e) => {
    e.preventDefault();
    if (!running) return;
    if (Number(answer) === problem.v) {
      setScore((s) => s + 1);
      setAnswer("");
      setProblem(gen());
    } else {
      setAnswer("");
    }
  };

  return (
    <div className="card" style={{ textAlign: "center", maxWidth: 480, margin: "0 auto" }}>
      <div className="card-title" style={{ justifyContent: "center" }}>Quick Math · 30 seconds</div>
      <div className="grid grid-cols-2 mb-16">
        <div className="card stat" style={{ padding: 14 }}>
          <div className="label">Score</div>
          <div className="value green">{score}</div>
        </div>
        <div className="card stat" style={{ padding: 14 }}>
          <div className="label">Time left</div>
          <div className={"value " + (time <= 5 ? "red" : "")}>{time}s</div>
        </div>
      </div>

      {!running ? (
        <button className="btn" onClick={start} style={{ padding: "12px 28px", fontSize: 16 }}>
          {score > 0 ? `Try again (last: ${score})` : "Start"}
        </button>
      ) : (
        <form onSubmit={submit}>
          <div style={{ fontSize: 42, fontWeight: 700, marginBottom: 16, letterSpacing: ".02em" }}>
            {problem.a} {problem.op} {problem.b} = ?
          </div>
          <input type="number" inputMode="numeric"
                 className="input tabular"
                 value={answer} onChange={(e) => setAnswer(e.target.value)}
                 style={{ fontSize: 24, textAlign: "center", maxWidth: 160, margin: "0 auto" }}
                 autoFocus/>
        </form>
      )}
    </div>
  );
}

/* ---------- Reaction Time ---------- */
function ReactionTime() {
  const [stage, setStage] = useState("idle");  // idle | wait | go | done | early
  const [delay, setDelay] = useState(0);
  const [start, setStart] = useState(0);
  const [result, setResult] = useState(null);
  const [best, setBest] = useState(null);
  const t = useRef(null);

  const begin = () => {
    setStage("wait");
    setResult(null);
    const d = 1500 + Math.random() * 2500;
    setDelay(d);
    t.current = setTimeout(() => {
      setStart(Date.now());
      setStage("go");
    }, d);
  };

  const click = () => {
    if (stage === "wait") {
      clearTimeout(t.current);
      setStage("early");
    } else if (stage === "go") {
      const ms = Date.now() - start;
      setResult(ms);
      setBest((b) => b === null ? ms : Math.min(b, ms));
      setStage("done");
    }
  };

  const colors = {
    idle:  { bg: "var(--surface-2)", txt: "Tap to start" },
    wait:  { bg: "var(--red-bg)",    txt: "Wait for green…" },
    go:    { bg: "var(--green-bg)",  txt: "TAP NOW!" },
    done:  { bg: "var(--surface-2)", txt: `${result}ms — tap for again` },
    early: { bg: "var(--red-bg)",    txt: "Too early! tap to retry" },
  }[stage];

  return (
    <div className="card" style={{ textAlign: "center" }}>
      <div className="card-title" style={{ justifyContent: "center" }}>
        Reaction Time {best !== null && <span className="text-3" style={{ marginLeft: 8 }}>· best: {best}ms</span>}
      </div>
      <button onClick={stage === "idle" || stage === "done" || stage === "early" ? begin : click}
              style={{
                width: "100%", padding: "100px 0",
                fontSize: 24, fontWeight: 700,
                color: "var(--text)",
                background: colors.bg,
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                cursor: "pointer",
                fontFamily: "inherit",
              }}>
        {colors.txt}
      </button>
    </div>
  );
}
