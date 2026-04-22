import { useState } from 'react'

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

const NAV_ITEMS = [
    { id: 'general', icon: 'settings', label: 'General' },
    { id: 'voice', icon: 'volume_up', label: 'Voice & Audio' },
    { id: 'ai', icon: 'psychology', label: 'AI & Brain' },
    { id: 'appearance', icon: 'palette', label: 'Appearance' },
    { id: 'api', icon: 'key', label: 'API Keys' },
    { id: 'about', icon: 'info', label: 'About' },
]

const AI_MODELS = ['CLAUDE_3_SONNET', 'CLAUDE_3_OPUS', 'GPT_4_OMNI']
const MEMORY_OPTS = ['Last 50 Exchanges', 'Full Session Only', 'Persistent Vault']
const VOICE_MODELS = ['Jarvis_Classic (V1)', 'Warm_Synth (V2)', 'Custom_Upload...']
const MIC_OPTS = ['Studio_Mic_PRO', 'Internal_Array']
const SPK_OPTS = ['Digital_Output', 'System_Def']
const LANG_OPTS = ['English (US)', 'Hindi (IN)', 'Spanish (ES)']

const API_KEYS = [
    { id: 'anthropic', label: 'ANTHROPIC_SECRET', placeholder: 'sk-ant-v1-••••••••' },
    { id: 'elevenlabs', label: 'ELEVENLABS_ID', placeholder: 'el-key-••••••••' },
    { id: 'picvoice', label: 'PIC_VOICE_PLATFORM', placeholder: 'pv-key-••••••••' },
    { id: 'brave', label: 'BRAVE_SEARCH_API', placeholder: 'br-key-••••••••' },
]

const WAVEFORM_BARS = [1, 3, 2, 4, 6, 5, 3, 1, 2, 4]

// ─────────────────────────────────────────────
// REUSABLE PRIMITIVES
// ─────────────────────────────────────────────

/** Chamfer-cut card with cyan bracket corners */
function Card({ children, className = '' }) {
    return (
        <div
            className={`relative p-6 bg-surface-container-low/40 backdrop-blur-md border border-outline-variant/15 ${className}`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 15px) 0, 100% 15px, 100% 100%, 15px 100%, 0 calc(100% - 15px))' }}
        >
            {/* bracket corners */}
            <span className="absolute top-0 left-0 w-[10px] h-[10px] border-t-2 border-l-2 border-primary" />
            <span className="absolute bottom-0 right-0 w-[10px] h-[10px] border-b-2 border-r-2 border-primary" />
            {children}
        </div>
    )
}

/** Section heading */
function CardHeading({ icon, label }) {
    return (
        <h2 className="text-base font-headline font-bold text-primary mb-6 uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">{icon}</span>
            {label}
        </h2>
    )
}

/** Styled select dropdown */
function HudSelect({ label, options, value, onChange }) {
    return (
        <div className="space-y-2">
            {label && <label className="block text-[10px] font-label text-on-surface-variant tracking-[0.2em] uppercase">{label}</label>}
            <div className="relative">
                <select
                    value={value}
                    onChange={e => onChange?.(e.target.value)}
                    className="w-full bg-surface-container-highest border-b-2 border-primary-dim/30 text-on-surface p-3 font-body text-sm focus:border-primary focus:ring-0 transition-all outline-none appearance-none cursor-pointer"
                >
                    {options.map(o => <option key={o}>{o}</option>)}
                </select>
                <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-primary/50 text-sm pointer-events-none">expand_more</span>
            </div>
        </div>
    )
}

/** Slider with label + value badge */
function HudSlider({ label, value, onChange, min = 1, max = 3, marks }) {
    return (
        <div className="space-y-3">
            <div className="flex justify-between items-center">
                <label className="text-[10px] font-label text-on-surface-variant tracking-[0.2em] uppercase">{label}</label>
                <span className="text-[10px] text-primary font-label">{value}</span>
            </div>
            <input
                type="range"
                min={min}
                max={max}
                value={typeof value === 'number' ? value : 2}
                onChange={e => onChange?.(e.target.value)}
                className="w-full h-1 bg-surface-container-highest appearance-none cursor-pointer accent-primary"
            />
            {marks && (
                <div className="flex justify-between text-[8px] font-label text-slate-600">
                    {marks.map(m => <span key={m}>{m}</span>)}
                </div>
            )}
        </div>
    )
}

/** Toggle switch */
function HudToggle({ label, checked, onChange }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-xs font-label text-on-surface tracking-wider uppercase">{label}</span>
            <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={checked} onChange={e => onChange?.(e.target.checked)} />
                <div className="w-10 h-5 bg-surface-container-highest peer-checked:bg-primary/20 relative
          after:content-[''] after:absolute after:top-[2px] after:left-[2px]
          after:bg-on-surface-variant peer-checked:after:bg-primary
          after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
            </label>
        </div>
    )
}

/** Password API key row */
function ApiKeyRow({ label, placeholder, visible, onToggleVisible, onVerify }) {
    return (
        <div className="space-y-1">
            <label className="text-[9px] font-label text-slate-500 uppercase tracking-widest">{label}</label>
            <div className="flex gap-2">
                <div className="flex-1 bg-surface-container-highest border-b border-primary/20 flex items-center px-3">
                    <input
                        type={visible ? 'text' : 'password'}
                        defaultValue={placeholder}
                        className="bg-transparent border-none text-xs w-full focus:ring-0 outline-none text-on-surface"
                    />
                    <button onClick={onToggleVisible}>
                        <span className="material-symbols-outlined text-sm text-slate-500 hover:text-primary transition-colors">
                            {visible ? 'visibility_off' : 'visibility'}
                        </span>
                    </button>
                </div>
                <button
                    onClick={onVerify}
                    className="px-4 py-2 bg-primary/10 border border-primary/30 text-primary text-[10px] font-bold hover:bg-primary/20 transition-all"
                >
                    VERIFY
                </button>
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────
// SECTION PANELS
// ─────────────────────────────────────────────

function GeneralParameters() {
    const [lang, setLang] = useState('English (US)')
    const [sensitivity, setSens] = useState(2)
    const [startOS, setStartOS] = useState(true)
    const [alwaysTop, setAlways] = useState(false)

    const sensLabel = ['', 'LOW', 'MED', 'HIGH'][sensitivity] ?? 'MED'

    return (
        <Card>
            <CardHeading icon="settings" label="General_Parameters" />
            <div className="space-y-8">
                <HudSelect label="Primary_Language" options={LANG_OPTS} value={lang} onChange={setLang} />
                <HudSlider
                    label="Wake_Word_Sensitivity"
                    value={sensLabel}
                    min={1} max={3}
                    onChange={v => setSens(Number(v))}
                    marks={['LOW', 'MED', 'HIGH']}
                />
                <div className="space-y-4 pt-2">
                    <HudToggle label="Start_With_OS" checked={startOS} onChange={setStartOS} />
                    <HudToggle label="Always_On_Top" checked={alwaysTop} onChange={setAlways} />
                </div>
            </div>
        </Card>
    )
}

function VoiceAcoustics() {
    const [mic, setMic] = useState('Studio_Mic_PRO')
    const [spk, setSpk] = useState('Digital_Output')
    const [model, setModel] = useState('Jarvis_Classic (V1)')
    const [speed, setSpeed] = useState(2)

    const speedLabel = ['', '0.8X', '1.0X', '1.2X', '1.5X', '2.0X'][speed] ?? '1.2X'

    return (
        <Card>
            <CardHeading icon="volume_up" label="Voice_&_Acoustics" />
            <div className="space-y-6">
                {/* Mic + Speaker row */}
                <div className="grid grid-cols-2 gap-4">
                    <HudSelect label="Mic_Input" options={MIC_OPTS} value={mic} onChange={setMic} />
                    <HudSelect label="Speaker_Out" options={SPK_OPTS} value={spk} onChange={setSpk} />
                </div>

                <HudSelect label="Voice_Model" options={VOICE_MODELS} value={model} onChange={setModel} />

                <HudSlider
                    label="Speaking_Speed"
                    value={speedLabel}
                    min={1} max={5}
                    onChange={v => setSpeed(Number(v))}
                />

                {/* Volume waveform visualizer */}
                <div className="space-y-3">
                    <label className="block text-[10px] font-label text-on-surface-variant tracking-[0.2em] uppercase">Master_Volume</label>
                    <div className="flex items-end gap-[3px] h-8 mb-2">
                        {WAVEFORM_BARS.map((h, i) => (
                            <div
                                key={i}
                                className={`flex-1 ${i < 7 ? 'bg-primary' : 'bg-primary/30'}`}
                                style={{ height: `${h * 5}px` }}
                            />
                        ))}
                    </div>
                    <input type="range" className="w-full h-1 bg-surface-container-highest appearance-none cursor-pointer accent-primary" />
                </div>

                <button className="w-full py-2 border border-primary/40 text-primary font-label uppercase text-xs tracking-widest hover:bg-primary/10 transition-all">
                    TEST_VOICE_MODULE
                </button>
            </div>
        </Card>
    )
}

function CognitionCore() {
    const [aiModel, setAiModel] = useState('CLAUDE_3_SONNET')
    const [density, setDensity] = useState(2)
    const [memory, setMemory] = useState('Last 50 Exchanges')
    const [showPurge, setShowPurge] = useState(false)

    const densityLabel = ['', 'BRIEF', 'NORMAL', 'DETAILED'][density] ?? 'NORMAL'

    return (
        <Card>
            <CardHeading icon="psychology" label="Cognition_Core" />
            <div className="space-y-6">
                <HudSelect label="AI_Model_Architecture" options={AI_MODELS} value={aiModel} onChange={setAiModel} />

                <HudSlider
                    label="Response_Density"
                    value={densityLabel}
                    min={1} max={3}
                    onChange={v => setDensity(Number(v))}
                    marks={['BRIEF', 'NORMAL', 'DETAILED']}
                />

                <HudSelect label="Memory_Retention" options={MEMORY_OPTS} value={memory} onChange={setMemory} />

                <div className="pt-2">
                    {!showPurge ? (
                        <button
                            onClick={() => setShowPurge(true)}
                            className="w-full py-3 bg-error-container/20 text-error border border-error/30 font-headline font-bold text-xs tracking-[0.2em] hover:bg-error-container/40 transition-all"
                        >
                            PURGE_SYSTEM_MEMORY
                        </button>
                    ) : (
                        <div className="border border-error/40 p-4 space-y-3">
                            <p className="text-[10px] font-label text-error uppercase tracking-wider">Confirm memory purge? This cannot be undone.</p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowPurge(false)}
                                    className="flex-1 py-2 border border-outline-variant/30 text-on-surface-variant font-label text-xs uppercase tracking-wider hover:bg-surface-container-high transition-all"
                                >
                                    CANCEL
                                </button>
                                <button
                                    onClick={() => setShowPurge(false)}
                                    className="flex-1 py-2 bg-error/20 text-error border border-error/50 font-headline font-bold text-xs tracking-wider hover:bg-error/30 transition-all"
                                >
                                    CONFIRM
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </Card>
    )
}

function ApiAccessNodes() {
    const [visibility, setVisibility] = useState({})

    const toggleVisible = id =>
        setVisibility(prev => ({ ...prev, [id]: !prev[id] }))

    return (
        <Card>
            <CardHeading icon="key" label="API_Access_Nodes" />
            {/* Info banner */}
            <div className="bg-primary/5 border-l-2 border-primary p-3 mb-6">
                <p className="text-[10px] font-body text-primary/80 leading-relaxed italic">
                    "API keys are stored locally within the encrypted OS vault. No keys are transmitted to external servers."
                </p>
            </div>
            <div className="space-y-5">
                {API_KEYS.map(k => (
                    <ApiKeyRow
                        key={k.id}
                        label={k.label}
                        placeholder={k.placeholder}
                        visible={!!visibility[k.id]}
                        onToggleVisible={() => toggleVisible(k.id)}
                        onVerify={() => { }}
                    />
                ))}
            </div>
        </Card>
    )
}

// ─────────────────────────────────────────────
// ROOT EXPORT
// ─────────────────────────────────────────────

/**
 * SettingsPage.jsx — SYNTHETIC_INTEL // JARVIS_OS Settings
 *
 * Props (all optional):
 *   activeSection: string   — currently selected nav item id
 *   userAvatar:    string   — img src for top-right avatar
 */
export default function SettingsPage({
    activeSection: _active = 'ai',
    userAvatar,
}) {
    const [activeSection, setActiveSection] = useState(_active)

    return (
        <div
            className="relative min-h-screen overflow-hidden bg-[#0e0e13] text-on-background font-body"
            style={{
                backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(110,221,255,0.05) 1px, transparent 0)',
                backgroundSize: '24px 24px',
            }}
        >
            {/* Large grid overlay */}
            <div
                className="fixed inset-0 pointer-events-none z-0 opacity-20"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(110,221,255,0.05) 1px,transparent 1px),linear-gradient(90deg,rgba(110,221,255,0.05) 1px,transparent 1px)',
                    backgroundSize: '100px 100px',
                }}
            />

            {/* ── Top Nav ── */}
            <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-[#0e0e13]/80 backdrop-blur-xl border-b border-[#00d4ff]/15 shadow-[0_0_15px_rgba(0,212,255,0.08)]">
                <div className="flex items-center gap-8">
                    <span className="text-2xl font-bold tracking-tighter text-[#00d4ff] uppercase font-headline">
                        SYNTHETIC_INTEL
                    </span>
                    <div className="hidden md:flex gap-6">
                        {['SYSTEM_STATUS', 'CORE_LOGS'].map(t => (
                            <a key={t} href="#" className="text-slate-500 font-label tracking-widest text-xs hover:text-[#00d4ff] transition-all">{t}</a>
                        ))}
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <button className="text-slate-500 hover:text-[#00d4ff] transition-all">
                        <span className="material-symbols-outlined">settings_input_component</span>
                    </button>
                    <button className="text-slate-500 hover:text-[#00d4ff] transition-all">
                        <span className="material-symbols-outlined">notifications_none</span>
                    </button>
                    <div className="w-8 h-8 bg-surface-container-highest border border-primary/20 flex items-center justify-center overflow-hidden">
                        {userAvatar ? (
                            <img src={userAvatar} alt="User" className="w-full h-full object-cover grayscale brightness-125" />
                        ) : (
                            <span className="material-symbols-outlined text-primary text-sm">person</span>
                        )}
                    </div>
                </div>
            </nav>

            {/* ── Layout: Sidebar + Main ── */}
            <div className="flex pt-16 h-screen overflow-hidden relative z-10">

                {/* ── Side Nav ── */}
                <aside className="w-64 bg-[#131319] border-r border-[#00d4ff]/10 flex flex-col py-4 shrink-0 overflow-y-auto">
                    {/* Brand */}
                    <div className="px-6 mb-8">
                        <div className="flex items-center gap-3 mb-1">
                            <span className="material-symbols-outlined text-[#00d4ff]" style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
                            <span className="text-lg font-black text-[#00d4ff] font-headline">JARVIS_OS</span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-label tracking-[0.2em]">V.2.0.4_BETA</span>
                    </div>

                    {/* Nav links */}
                    <nav className="flex-1 space-y-1">
                        {NAV_ITEMS.map(item => (
                            <button
                                key={item.id}
                                onClick={() => setActiveSection(item.id)}
                                className={`w-full flex items-center gap-3 px-6 py-3 font-label uppercase text-xs tracking-[0.1em] transition-colors duration-200 ${activeSection === item.id
                                        ? 'bg-[#1f1f26] text-[#00d4ff] border-l-4 border-[#00d4ff]'
                                        : 'text-slate-400 hover:bg-[#1f1f26] hover:text-[#00d4ff]'
                                    }`}
                            >
                                <span className="material-symbols-outlined text-sm">{item.icon}</span>
                                {item.label}
                            </button>
                        ))}
                    </nav>

                    {/* Footer actions */}
                    <div className="px-4 py-6 mt-auto border-t border-white/5 space-y-1">
                        <button className="w-full bg-primary text-on-primary py-2 font-headline font-bold text-xs tracking-widest mb-4 hover:shadow-[0_0_15px_#6dddff] transition-all">
                            INITIATE_SYNC
                        </button>
                        <a href="#" className="flex items-center gap-3 px-2 py-2 text-slate-400 font-label uppercase text-[10px] tracking-[0.1em] hover:text-[#00d4ff]">
                            <span className="material-symbols-outlined text-sm">help_outline</span> Support
                        </a>
                        <a href="#" className="flex items-center gap-3 px-2 py-2 text-error-dim font-label uppercase text-[10px] tracking-[0.1em] hover:text-error transition-colors">
                            <span className="material-symbols-outlined text-sm">logout</span> Sign Out
                        </a>
                    </div>
                </aside>

                {/* ── Main Content ── */}
                <main className="flex-1 overflow-y-auto bg-[#0e0e13] p-8 pb-24">
                    <div className="max-w-4xl mx-auto">

                        {/* Page Header */}
                        <header className="mb-12">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-[10px] text-primary font-label tracking-[0.3em]">SYSTEM // PREFERENCES</span>
                                <div className="h-px flex-1 bg-gradient-to-r from-primary/30 to-transparent" />
                            </div>
                            <h1 className="text-4xl font-headline font-black text-on-background tracking-tighter uppercase">
                                AI &amp; Brain_Configuration
                            </h1>
                        </header>

                        {/* 2-column grid of setting cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                            {/* Left column */}
                            <section className="space-y-6">
                                <GeneralParameters />
                                <VoiceAcoustics />
                            </section>

                            {/* Right column */}
                            <section className="space-y-6">
                                <CognitionCore />
                                <ApiAccessNodes />
                            </section>

                        </div>

                        {/* Footer telemetry */}
                        <footer className="mt-12 flex items-center justify-between border-t border-primary/10 pt-6">
                            <div className="flex gap-8">
                                <div>
                                    <span className="block text-[8px] font-label text-slate-600 uppercase tracking-widest">OS_STABILITY</span>
                                    <span className="text-xs font-label text-primary">99.98% NOMINAL</span>
                                </div>
                                <div>
                                    <span className="block text-[8px] font-label text-slate-600 uppercase tracking-widest">SEC_LATENCY</span>
                                    <span className="text-xs font-label text-primary">14MS</span>
                                </div>
                            </div>
                            <div className="text-[10px] font-label text-slate-500">
                                DESIGNED_FOR_SYNTHETIC_INTEL // 2024
                            </div>
                        </footer>

                    </div>
                </main>
            </div>
        </div>
    )
}