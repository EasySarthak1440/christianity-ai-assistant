import { useState, useEffect } from "react"
import { BookOpen } from "lucide-react"

const API = "https://d2vdkua64gpad1.cloudfront.net"

const containerStyle = {
  padding: "12px 14px",
  borderRadius: "10px",
  background: "rgba(255,255,255,0.025)",
  border: "1px solid rgba(255,255,255,0.07)",
}

const labelStyle = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
  fontSize: "11px",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#94a3b8",
  marginBottom: "10px",
}

const optionStyle = (active) => ({
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "8px 10px",
  borderRadius: "7px",
  cursor: "pointer",
  fontSize: "12px",
  color: active ? "#06b6d4" : "#94a3b8",
  background: active ? "rgba(6,182,212,0.12)" : "transparent",
  border: active ? "1px solid rgba(6,182,212,0.25)" : "1px solid transparent",
  transition: "all .15s",
  marginBottom: "4px",
})

const dotStyle = (active) => ({
  width: "8px",
  height: "8px",
  borderRadius: "50%",
  background: active ? "#06b6d4" : "rgba(255,255,255,0.12)",
  flexShrink: 0,
})

export default function DenominationSelector({ value, onChange }) {
  const [denoms, setDenoms] = useState([])

  useEffect(() => {
    fetch(`${API}/christianity/denominations`)
      .then((r) => r.json())
      .then((d) => setDenoms(d.denominations || []))
      .catch(() => {})
  }, [])

  return (
    <div style={containerStyle}>
      <div style={labelStyle}>
        <BookOpen size={13} />
        <span>Tradition</span>
      </div>
      {(denoms.length > 0 ? denoms : [
        { id: "general", label: "General", description: "Neutral" },
        { id: "catholic", label: "Catholic", description: "Papal authority" },
        { id: "orthodox", label: "Orthodox", description: "Eastern tradition" },
        { id: "protestant", label: "Protestant", description: "Sola Scriptura" },
      ]).map((d) => (
        <div
          key={d.id}
          style={optionStyle(value === d.id)}
          onClick={() => onChange(d.id)}
          onMouseEnter={(e) => {
            if (value !== d.id) e.currentTarget.style.background = "rgba(255,255,255,0.04)"
          }}
          onMouseLeave={(e) => {
            if (value !== d.id) e.currentTarget.style.background = "transparent"
          }}
        >
          <div style={dotStyle(value === d.id)} />
          <div>
            <div style={{ fontWeight: 500, fontSize: "12px", lineHeight: 1.4 }}>{d.label}</div>
            <div style={{ fontSize: "10px", color: "#64748b", marginTop: "1px" }}>
              {d.description}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
