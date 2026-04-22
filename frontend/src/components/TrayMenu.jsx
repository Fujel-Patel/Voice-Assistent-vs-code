import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

/**
 * TrayMenu.jsx — System tray popup component
 *
 * Displayed from the system tray icon in Electron. Shows app status,
 * quick-action menu items, toggle switches, and version info.
 *
 * Props:
 *   isOpen:           boolean — whether the tray menu is visible
 *   isListening:      boolean — voice listening toggle state
 *   isMuted:          boolean — mute toggle state
 *   onToggleListening: () => void
 *   onToggleMute:     () => void
 *   onShowWindow:     () => void
 *   onOpenActivityLog: () => void
 *   onOpenSettings:   () => void
 *   onQuit:           () => void
 *   version:          string — e.g. "V1.0.0"
 *   lastActive:       string — e.g. "2M AGO"
 */

const MENU_ITEMS_VARIANTS = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.04, delayChildren: 0.1 },
  },
}

const ITEM_VARIANTS = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export default function TrayMenu({
  isOpen = true,
  isListening = true,
  isMuted = false,
  onToggleListening,
  onToggleMute,
  onShowWindow,
  onOpenActivityLog,
  onOpenSettings,
  onQuit,
  version = 'V1.0.0',
  lastActive = '2M AGO',
}) {
  const [expanded, setExpanded] = useState(true)
  const menuRef = useRef(null)

  /* Close on outside click (Electron context) */
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        // Could send IPC to close tray window
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={menuRef}
          initial={{ opacity: 0, y: 10, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.96 }}
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
          className="w-[300px] bg-[#0e0e13]/95 backdrop-blur-2xl border border-primary/15 shadow-2xl flex flex-col overflow-hidden select-none"
          style={{ fontFamily: "'Space Grotesk', sans-serif" }}
        >
          {/* ── Header ── */}
          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center gap-3 px-5 py-4 w-full text-left hover:bg-primary/5 transition-colors"
          >
            {/* Logo icon */}
            <div className="w-9 h-9 bg-primary/15 border border-primary/30 flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-primary text-xl">
                neurology
              </span>
            </div>

            {/* Title + status */}
            <div className="flex-1 min-w-0">
              <h3 className="font-headline text-sm font-bold text-primary tracking-widest uppercase leading-tight">
                SYNTH_AI_OS
              </h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                <span className="text-[9px] font-label text-green-400 uppercase tracking-widest">
                  Core Active
                </span>
              </div>
            </div>

            {/* Chevron */}
            <motion.span
              animate={{ rotate: expanded ? 0 : -90 }}
              transition={{ duration: 0.2 }}
              className="material-symbols-outlined text-primary/50 text-lg"
            >
              expand_more
            </motion.span>
          </button>

          {/* ── Menu Items ── */}
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={MENU_ITEMS_VARIANTS}
                className="flex flex-col"
              >
                {/* Divider */}
                <div className="h-px w-full bg-gradient-to-r from-primary/30 via-primary/10 to-transparent" />

                {/* Listening toggle */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayToggleItem
                    icon="mic"
                    label="Listening"
                    checked={isListening}
                    onChange={onToggleListening}
                    highlight
                  />
                </motion.div>

                {/* Divider */}
                <div className="h-px mx-4 bg-outline-variant/15" />

                {/* Show Window */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayMenuItem
                    icon="open_in_new"
                    label="Show Window"
                    shortcut="CTRL+SHIFT+J"
                    onClick={onShowWindow}
                  />
                </motion.div>

                {/* Mute */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayMenuItem
                    icon={isMuted ? 'volume_off' : 'volume_up'}
                    label={isMuted ? 'Unmute' : 'Mute'}
                    onClick={onToggleMute}
                  />
                </motion.div>

                {/* Activity Log */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayMenuItem
                    icon="receipt_long"
                    label="Activity Log"
                    hasSubmenu
                    onClick={onOpenActivityLog}
                  />
                </motion.div>

                {/* Settings */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayMenuItem
                    icon="settings"
                    label="Settings"
                    onClick={onOpenSettings}
                  />
                </motion.div>

                {/* Divider */}
                <div className="h-px mx-4 bg-outline-variant/15" />

                {/* Quit */}
                <motion.div variants={ITEM_VARIANTS}>
                  <TrayMenuItem
                    icon="power_settings_new"
                    label="Quit Jarvis"
                    danger
                    onClick={onQuit}
                  />
                </motion.div>

                {/* ── Footer ── */}
                <motion.div
                  variants={ITEM_VARIANTS}
                  className="flex items-center justify-between px-5 py-2 bg-[#0a0a0f] border-t border-primary/10"
                >
                  <span className="text-[8px] font-mono text-on-surface-variant/50 uppercase tracking-wider">
                    {version} — STABLE
                  </span>
                  <span className="text-[8px] font-mono text-on-surface-variant/50 uppercase tracking-wider">
                    LAST_ACTIVE: {lastActive}
                  </span>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ── Menu Item ─────────────────────────────────────────────── */
function TrayMenuItem({ icon, label, shortcut, hasSubmenu, danger, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 w-full px-5 py-3 text-left transition-colors
        ${danger
          ? 'text-error/80 hover:text-error hover:bg-error/5'
          : 'text-on-surface/80 hover:text-primary hover:bg-primary/5'
        }`}
    >
      <span
        className={`material-symbols-outlined text-lg ${
          danger ? 'text-error/60' : 'text-primary/50'
        }`}
      >
        {icon}
      </span>

      <span className="flex-1 text-sm font-body tracking-wide">{label}</span>

      {shortcut && (
        <span className="text-[8px] font-mono text-on-surface-variant/40 bg-surface-container-highest px-2 py-0.5 border border-outline-variant/20 uppercase tracking-wider">
          {shortcut}
        </span>
      )}

      {hasSubmenu && (
        <span className="material-symbols-outlined text-sm text-on-surface-variant/30">
          chevron_right
        </span>
      )}
    </button>
  )
}

/* ── Toggle Item ───────────────────────────────────────────── */
function TrayToggleItem({ icon, label, checked, onChange, highlight }) {
  return (
    <button
      onClick={onChange}
      className={`flex items-center gap-3 w-full px-5 py-3 text-left transition-colors
        ${highlight && checked
          ? 'bg-primary/8 text-primary'
          : 'text-on-surface/80 hover:text-primary hover:bg-primary/5'
        }`}
    >
      <span className="material-symbols-outlined text-lg text-primary/70">{icon}</span>
      <span className="flex-1 text-sm font-body tracking-wide">{label}</span>

      {/* Toggle switch */}
      <div
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
          checked ? 'bg-primary/30' : 'bg-surface-container-highest'
        }`}
      >
        <motion.div
          className="absolute top-0.5 w-4 h-4 rounded-full"
          animate={{
            left: checked ? 22 : 2,
            backgroundColor: checked ? '#6dddff' : '#48474d',
            boxShadow: checked
              ? '0 0 8px rgba(109, 221, 255, 0.6)'
              : '0 0 0px transparent',
          }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </div>
    </button>
  )
}
