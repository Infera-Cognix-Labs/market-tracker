"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { ChevronDown, Check } from "lucide-react"
import { T } from "./DesignTokens"

export interface DropdownOption {
  value: string | number
  label: string
}

interface DropdownProps {
  value: string | number
  onChange: (value: string | number) => void
  options: DropdownOption[]
  label?: string
  placeholder?: string
  disabled?: boolean
  style?: React.CSSProperties
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 99,
}

const listContainerStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  right: 0,
  marginTop: 4,
  background: T.bg3,
  border: `1px solid ${T.border2}`,
  borderRadius: 8,
  maxHeight: 200,
  overflowY: "auto",
  zIndex: 100,
  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
}

export const Dropdown = ({ value, onChange, options, label, placeholder, disabled, style }: DropdownProps) => {
  const [open, setOpen] = useState(false)
  const [highlightIdx, setHighlightIdx] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const selected = options.find(o => o.value === value)
  const displayLabel = selected?.label ?? placeholder ?? "Select..."

  const close = useCallback(() => {
    setOpen(false)
    setHighlightIdx(-1)
  }, [])

  useEffect(() => {
    if (!open) return
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        close()
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [open, close])

  useEffect(() => {
    if (open && highlightIdx >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-option]")
      items[highlightIdx]?.scrollIntoView({ block: "nearest" })
    }
  }, [open, highlightIdx])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault()
        setOpen(true)
        const idx = options.findIndex(o => o.value === value)
        setHighlightIdx(idx >= 0 ? idx : 0)
      }
      return
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setHighlightIdx(prev => (prev + 1) % options.length)
        break
      case "ArrowUp":
        e.preventDefault()
        setHighlightIdx(prev => (prev - 1 + options.length) % options.length)
        break
      case "Enter":
      case " ":
        e.preventDefault()
        if (highlightIdx >= 0 && highlightIdx < options.length) {
          onChange(options[highlightIdx].value)
          close()
        }
        break
      case "Escape":
        e.preventDefault()
        close()
        break
    }
  }

  return (
    <div ref={containerRef} style={{ position: "relative", ...style }}>
      {label && (
        <label style={{
          display: "block", fontSize: 11, fontWeight: 600, color: T.text2,
          marginBottom: 5, letterSpacing: ".04em", textTransform: "uppercase" as const,
        }}>
          {label}
        </label>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => { if (!disabled) setOpen(prev => !prev) }}
        onKeyDown={handleKeyDown}
        style={{
          width: "100%", padding: "9px 12px", borderRadius: 8,
          border: `1px solid ${open ? T.blue : T.border}`,
          background: T.bg3, color: selected ? T.text0 : T.text2,
          fontSize: 13, fontFamily: T.sans, outline: "none", cursor: disabled ? "not-allowed" : "pointer",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          textAlign: "left", transition: "border-color .15s",
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {displayLabel}
        </span>
        <ChevronDown size={14} style={{ color: T.text3, flexShrink: 0, marginLeft: 8, transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform .15s" }} />
      </button>

      {open && (
        <>
          <div style={overlayStyle} onClick={close} />
          <div ref={listRef} style={listContainerStyle} role="listbox">
            {options.map((opt, i) => {
              const isSelected = opt.value === value
              const isHighlight = i === highlightIdx
              return (
                <div
                  key={opt.value}
                  data-option
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => { onChange(opt.value); close() }}
                  onMouseEnter={() => setHighlightIdx(i)}
                  style={{
                    padding: "8px 12px", cursor: "pointer", fontSize: 13, fontFamily: T.sans,
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    color: isSelected ? T.text0 : T.text1,
                    background: isHighlight ? T.bg4 : "transparent",
                    transition: "background .1s",
                    borderBottom: `1px solid ${T.border}`,
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {opt.label}
                  </span>
                  {isSelected && <Check size={13} style={{ color: T.amber, flexShrink: 0, marginLeft: 8 }} />}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
