import { useState, useRef } from "react"
import { Image, Send, AlertCircle, Loader } from "lucide-react"

const API = "http://localhost:8000"

const glass = { background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.07)", backdropFilter: "blur(20px)" }

const sectionStyle = {
  padding: "12px 14px",
  borderRadius: "10px",
  ...glass,
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

const inputContainer = {
  display: "flex",
  gap: "8px",
  alignItems: "center",
}

const inputStyle = {
  flex: 1,
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px",
  padding: "8px 12px",
  color: "#e2e8f0",
  fontSize: "12px",
  fontFamily: "Inter, sans-serif",
  outline: "none",
  resize: "none",
}

const btnStyle = (disabled) => ({
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: "34px",
  height: "34px",
  borderRadius: "8px",
  border: "none",
  cursor: disabled ? "not-allowed" : "pointer",
  background: disabled ? "rgba(255,255,255,0.05)" : "#06b6d4",
  color: disabled ? "#64748b" : "#fff",
  opacity: disabled ? 0.5 : 1,
  transition: "all .2s",
  flexShrink: 0,
})

const imageContainer = {
  marginTop: "12px",
  borderRadius: "8px",
  overflow: "hidden",
  border: "1px solid rgba(255,255,255,0.1)",
}

const blockMsg = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
  marginTop: "10px",
  padding: "8px 10px",
  borderRadius: "6px",
  background: "rgba(239,68,68,0.1)",
  border: "1px solid rgba(239,68,68,0.2)",
  color: "#fca5a5",
  fontSize: "11px",
  lineHeight: 1.4,
}

export default function ImageGenerator({ token }) {
  const [prompt, setPrompt] = useState("")
  const [loading, setLoading] = useState(false)
  const [imageUrl, setImageUrl] = useState(null)
  const [error, setError] = useState(null)
  const [blocked, setBlocked] = useState(false)
  const inputRef = useRef(null)

  const generate = async () => {
    const p = prompt.trim()
    if (!p || loading) return
    setLoading(true)
    setError(null)
    setImageUrl(null)
    setBlocked(false)

    try {
      const res = await fetch(`${API}/christianity/generate-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ prompt: p }),
      })
      const data = await res.json()
      if (data.image_url) {
        setImageUrl(data.image_url)
      } else if (!data.allowed) {
        setBlocked(true)
        setError(data.message || data.reason)
      } else {
        setError(data.message || "Image generation unavailable")
      }
    } catch (e) {
      setError("Failed to reach backend")
    }
    setLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      generate()
    }
  }

  return (
    <div style={sectionStyle}>
      <div style={labelStyle}>
        <Image size={13} />
        <span>Christian Image Generator</span>
      </div>
      <div style={inputContainer}>
        <input
          ref={inputRef}
          style={inputStyle}
          placeholder="e.g. The Good Shepherd, Sermon on the Mount..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          style={btnStyle(!prompt.trim() || loading)}
          onClick={generate}
          disabled={!prompt.trim() || loading}
        >
          {loading ? <Loader size={15} style={{ animation: "spin 1s linear infinite" }} /> : <Send size={14} />}
        </button>
      </div>

      {blocked && error && (
        <div style={blockMsg}>
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {error && !blocked && (
        <div style={{ ...blockMsg, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", color: "#fcd34d" }}>
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {imageUrl && (
        <div style={imageContainer}>
          <img
            src={imageUrl}
            alt="Generated Christian artwork"
            style={{ width: "100%", height: "auto", display: "block" }}
          />
        </div>
      )}
    </div>
  )
}
