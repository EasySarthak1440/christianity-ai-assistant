import { BookOpen, CheckCircle, AlertCircle } from "lucide-react"

const cardStyle = {
  display: "flex",
  alignItems: "flexStart",
  gap: "10px",
  padding: "10px 12px",
  borderRadius: "8px",
  marginTop: "8px",
  background: "rgba(6,182,212,0.06)",
  border: "1px solid rgba(6,182,212,0.15)",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#cbd5e1",
}

const iconStyle = {
  flexShrink: 0,
  marginTop: "1px",
}

const refStyle = {
  fontWeight: 600,
  color: "#06b6d4",
  marginBottom: "3px",
  fontSize: "11px",
  letterSpacing: "0.02em",
}

const textStyle = {
  color: "#e2e8f0",
  fontStyle: "italic",
  marginBottom: "4px",
}

const badgeStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: "4px",
  fontSize: "10px",
  fontWeight: 600,
  padding: "2px 6px",
  borderRadius: "4px",
  background: "rgba(6,182,212,0.12)",
  color: "#22d3ee",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
}

const notFoundStyle = {
  display: "flex",
  alignItems: "flexStart",
  gap: "10px",
  padding: "10px 12px",
  borderRadius: "8px",
  marginTop: "8px",
  background: "rgba(245,158,11,0.06)",
  border: "1px solid rgba(245,158,11,0.15)",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#fcd34d",
}

export default function ScriptureCard({ reference, text, verified = true }) {
  if (!verified) {
    return (
      <div style={notFoundStyle}>
        <AlertCircle size={16} style={{ ...iconStyle, color: "#f59e0b" }} />
        <div>
          <div style={{ fontWeight: 600, fontSize: "11px", color: "#f59e0b", marginBottom: "3px" }}>
            {reference}
          </div>
          <div>Could not verify this reference in scripture.</div>
        </div>
      </div>
    )
  }

  return (
    <div style={cardStyle}>
      <BookOpen size={16} style={{ ...iconStyle, color: "#22d3ee" }} />
      <div>
        <div style={refStyle}>{reference}</div>
        <div style={textStyle}>"{text}"</div>
        <div style={badgeStyle}>
          <CheckCircle size={10} />
          <span>KJV Verified</span>
        </div>
      </div>
    </div>
  )
}
