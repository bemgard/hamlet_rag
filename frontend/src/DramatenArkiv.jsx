import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8000";

const SUGGESTED = [
  "Vad tyckte kritikerna om Peter Stormare?",
  "Hur beskrevs scenografin?",
  "Vad tyckte brittisk press?",
  "Vilka skådespelare deltog?",
];

const SOURCE_COLORS = [
  { bg: "#fdf6ec", border: "#d4a84b", num: "#8b5e1a" },
  { bg: "#eef4fb", border: "#7aafd4", num: "#1a5f8a" },
  { bg: "#f0f8f2", border: "#7ac495", num: "#1a6b45" },
  { bg: "#fbeef4", border: "#d47aaa", num: "#7a1a55" },
  { bg: "#f2f0fb", border: "#9a8fd4", num: "#3a1a8a" },
];

function SourceModal({ source, onClose }) {
  if (!source) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(42,26,10,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 1000, padding: "1rem",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "#fffdf5", borderRadius: 16,
          border: "1px solid #d4b86a", padding: "2rem",
          maxWidth: 480, width: "100%", position: "relative",
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 14, right: 14,
            background: "none", border: "none", cursor: "pointer",
            fontSize: 20, color: "#b8986a", lineHeight: 1,
          }}
        >✕</button>

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <span style={{ color: "#c8a96e", fontSize: 16 }}>✦</span>
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: "italic", fontSize: 14, color: "#8b5e1a" }}>
            Källdokument
          </span>
        </div>

        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: 20, fontWeight: 400, margin: "0 0 6px", color: "#2a1a0a", lineHeight: 1.3 }}>
          {source.rubrik || "Utan rubrik"}
        </p>
        <p style={{ fontSize: 13, color: "#7a5a30", fontStyle: "italic", margin: "0 0 24px" }}>
          {source.publikation}{source.datum ? ` · ${source.datum}` : ""}
        </p>

        <div style={{
          background: "#fdf3e0", border: "1px dashed #d4a84b",
          borderRadius: 10, padding: "1.25rem",
        }}>
          <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#7a4e10" }}>
            🗂 Originaldokument
          </p>
          <p style={{ margin: 0, fontSize: 13, color: "#5a3a10", lineHeight: 1.6 }}>
            I en fullständig implementation skulle originaltidningens inskannade sida visas här —
            som en klickbar bild direkt från Dramatens fysiska arkiv.
          </p>
        </div>

        <p style={{ margin: "16px 0 0", fontSize: 12, color: "#b8986a", fontStyle: "italic", textAlign: "center" }}>
          Funktionen är planerad för framtida version av systemet
        </p>
      </div>
    </div>
  );
}

function SourceCard({ source, index, onClick }) {
  const c = SOURCE_COLORS[index % SOURCE_COLORS.length];
  return (
    <div
      onClick={onClick}
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 10,
        padding: "12px 14px",
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        cursor: "pointer",
        transition: "transform .15s, box-shadow .15s",
      }}
      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = `0 4px 12px ${c.border}44`; }}
      onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
    >
      <div style={{
        width: 22, height: 22, borderRadius: "50%",
        background: c.border,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "'IM Fell English', Georgia, serif",
        fontWeight: 700, fontSize: 12, flexShrink: 0,
        color: "#fff",
      }}>
        {index + 1}
      </div>
      <div style={{ minWidth: 0, flex: 1 }}>
        {source.rubrik && (
          <p style={{ margin: "0 0 3px", fontWeight: 600, fontSize: 13, color: "#2a1a0a", lineHeight: 1.3 }}>
            {source.rubrik}
          </p>
        )}
        <p style={{ margin: 0, fontSize: 12, color: "#7a5a30", fontStyle: "italic" }}>
          {source.publikation}{source.datum ? ` · ${source.datum}` : ""}
        </p>
      </div>
      <span style={{ fontSize: 11, color: c.border, marginTop: 2, flexShrink: 0 }}>Öppna →</span>
    </div>
  );
}

function TypewriterText({ text }) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    setDisplayed("");
    setDone(false);
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) { clearInterval(id); setDone(true); }
    }, 10);
    return () => clearInterval(id);
  }, [text]);
  return (
    <span style={{ whiteSpace: "pre-wrap" }}>
      {displayed}
      {!done && <span style={{ animation: "blink 1s step-end infinite" }}>▌</span>}
    </span>
  );
}

export default function DramatenArkiv() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [error, setError] = useState(null);
  const [activeSource, setActiveSource] = useState(null);
  const inputRef = useRef(null);

  async function search(q) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setLoading(true);
    setAnswer(null);
    setSources([]);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/fraga`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fraga: trimmed }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setAnswer(data.svar ?? "Inget svar.");
      setSources(data.kallor ?? []);
    } catch (e) {
      setError(e.message || "Kunde inte ansluta till arkivet. Kontrollera att backend körs på port 8000.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    search(query);
  }

  return (
    <div style={{
      fontFamily: "'Crimson Pro', Georgia, serif",
      maxWidth: 740,
      margin: "0 auto",
      padding: "2.5rem 1.5rem 4rem",
      color: "#2a1a0a",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=IM+Fell+English:ital@0;1&display=swap');
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        .d-input {
          width: 100%; box-sizing: border-box;
          background: #fffdf8; border: 1.5px solid #c8a96e;
          border-radius: 10px; padding: 13px 90px 13px 46px;
          font-family: 'Crimson Pro', Georgia, serif; font-size: 17px;
          color: #2a1a0a; outline: none; transition: border-color .2s, box-shadow .2s;
        }
        .d-input:focus { border-color: #8b5e1a; box-shadow: 0 0 0 3px #e8d09a44; }
        .d-input::placeholder { color: #b8986a; }
        .d-input:disabled { opacity: 0.6; }
        .d-btn {
          position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
          background: #7a3b10; border: none; border-radius: 7px;
          padding: 7px 18px; color: #fff8ed;
          font-family: 'Crimson Pro', Georgia, serif; font-size: 14px; font-weight: 600;
          cursor: pointer; transition: background .15s, transform .1s;
          white-space: nowrap;
        }
        .d-btn:hover:not(:disabled) { background: #5a2a08; }
        .d-btn:active:not(:disabled) { transform: translateY(-50%) scale(0.97); }
        .d-btn:disabled { background: #c8a96e; cursor: not-allowed; }
        .d-chip {
          background: #fdf3e0; border: 1px solid #d4a84b; border-radius: 20px;
          padding: 5px 13px; font-size: 13px; color: #7a4e10;
          cursor: pointer; transition: background .15s;
          font-family: 'Crimson Pro', Georgia, serif; white-space: nowrap;
        }
        .d-chip:hover { background: #f5e4b8; }
        .answer-block { animation: fadeUp .35s ease; }
        .src-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
      `}</style>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "2.25rem" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <div style={{ height: 1, width: 40, background: "#c8a96e" }} />
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: 11, letterSpacing: 3, color: "#8b5e1a", textTransform: "uppercase" }}>
            Kungliga Dramatiska Teatern · 1788
          </span>
          <div style={{ height: 1, width: 40, background: "#c8a96e" }} />
        </div>
        <h1 style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: 38, fontWeight: 400, margin: "0 0 6px", color: "#2a1a0a", lineHeight: 1.05 }}>
          Dramaten Arkivet
        </h1>
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: "italic", fontSize: 15, color: "#8b5e1a", margin: 0 }}>
          AI-driven sökning i 250 år av teaterhistoria
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} style={{ position: "relative", marginBottom: "1rem" }}>
        <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", fontSize: 20, color: "#c8a96e", pointerEvents: "none" }}>
          ✦
        </span>
        <input
          ref={inputRef}
          className="d-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Fråga arkivet… t.ex. 'Vad tyckte kritikerna om Peter Stormare?'"
          disabled={loading}
          autoFocus
        />
        <button className="d-btn" type="submit" disabled={loading || !query.trim()}>
          {loading ? "Söker…" : "Sök"}
        </button>
      </form>

      {/* Suggested queries */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "1.75rem" }}>
        {SUGGESTED.map(s => (
          <button key={s} className="d-chip" onClick={() => { setQuery(s); search(s); }}>
            {s}
          </button>
        ))}
      </div>

      <div style={{ borderTop: "1px solid #e8d4aa", marginBottom: "1.5rem" }} />

      {/* Loading */}
      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "1rem 0", color: "#8b5e1a" }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}>
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          <span style={{ fontStyle: "italic", fontSize: 15 }}>Söker i arkivet…</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: "#fbeee8", border: "1px solid #e8a06a", borderRadius: 8, padding: "12px 16px", fontSize: 14, color: "#7a2a0a", lineHeight: 1.5 }}>
          <strong>Fel:</strong> {error}
        </div>
      )}

      {/* Answer */}
      {answer && !loading && (
        <div className="answer-block">
          <div style={{
            background: "#fffdf5",
            border: "1px solid #d4b86a",
            borderRadius: 12,
            padding: "1.5rem 1.75rem",
            marginBottom: "1.25rem",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <span style={{ color: "#c8a96e", fontSize: 16 }}>✦</span>
              <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: "italic", fontSize: 14, color: "#8b5e1a", letterSpacing: 0.5 }}>
                Svar från arkivet
              </span>
              <span style={{ marginLeft: "auto", fontSize: 11, color: "#b8986a", fontStyle: "italic" }}>
                AI-genererat · baserat på källmaterial
              </span>
            </div>
            <p style={{ margin: 0, fontSize: 17, lineHeight: 1.8, color: "#2a1a0a" }}>
              <TypewriterText text={answer} />
            </p>
          </div>

          {/* Sources */}
          {sources.length > 0 && (
            <div>
              <p style={{
                fontFamily: "'IM Fell English', Georgia, serif",
                fontStyle: "italic", fontSize: 14,
                color: "#8b5e1a", marginBottom: 10, letterSpacing: 0.3
              }}>
                Källor ({sources.length})
              </p>
              <div className="src-grid">
                {sources.map((src, i) => (
                  <SourceCard key={i} source={src} index={i} onClick={() => setActiveSource(src)} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!answer && !loading && !error && (
        <p style={{ textAlign: "center", fontStyle: "italic", color: "#b8986a", fontSize: 15, marginTop: "2rem" }}>
          Ställ en fråga om Ingmar Bergmans Hamlet-uppsättning från 1986
        </p>
      )}

      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />

      {/* Footer */}
      <div style={{ marginTop: "3rem", textAlign: "center", borderTop: "1px solid #e8d4aa", paddingTop: "1rem" }}>
        <p style={{ fontSize: 12, color: "#b8986a", fontStyle: "italic", margin: 0 }}>
          Svaren genereras av Gemma 2B och baseras enbart på Dramatens arkivmaterial.
          Verifiera alltid mot originalkällorna.
        </p>
      </div>
    </div>
  );
}