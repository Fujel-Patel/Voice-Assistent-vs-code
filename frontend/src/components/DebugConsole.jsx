import { useState, useRef, useEffect } from 'react'

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

const TABS = ['TERMINAL', 'TELEMETRY', 'WEBSOCKET', 'CORE']

const NAV_ITEMS = [
    { id: 'SYSLOG', icon: 'terminal' },
    { id: 'API_FLUX', icon: 'monitoring' },
    { id: 'WS_DEBUG', icon: 'settings_input_component' },
    { id: 'MEM_DUMP', icon: 'memory' },
    { id: 'V_SYNTH', icon: 'record_voice_over' },
]

const DEFAULT_CARDS = [
    { id: 'SEC_01', icon: 'hub', label: 'Grid Topology', description: 'Mapping neural pathways across local subnet clusters.' },
    { id: 'SEC_02', icon: 'security', label: 'Aegis Protocol', description: 'Active firewall scrubbing all incoming WebSocket frames.' },
    { id: 'SEC_03', icon: 'sensors', label: 'Biometry Flux', description: 'Real-time pulse monitoring of synthetic sub-processes.' },
]

const DEFAULT_STATS = [
    { label: 'CPU Usage', value: 82, color: 'bg-primary' },
    { label: 'Memory Load', value: 45, color: 'bg-secondary' },
    { label: 'Neural Sync', value: 99.9, color: 'bg-tertiary' },
]

const CONSOLE_TABS = ['Events', 'API Usage', 'WebSocket']

const TAG_COLORS = {
    SYSTEM: 'text-blue-400',
    STT: 'text-purple-400',
    CLAUDE: 'text-cyan-400',
    TTS: 'text-amber-400',
    ERROR: 'text-red-400',
}

const DEFAULT_LOGS = [
    { id: 1, time: '14:02:31.42', tag: 'SYSTEM', message: 'Core initialization sequence complete. Node 8080 standing by.', type: 'success' },
    { id: 2, time: '14:02:32.01', tag: 'STT', message: 'Audio stream detected. Speech-to-Text engine warm.', type: 'success' },
    { id: 3, time: '14:02:32.88', tag: 'CLAUDE', message: 'POST /v1/messages HTTP/1.1 - Sending prompt context (2,401 tokens).', type: 'success' },
    { id: 4, time: '14:02:34.15', tag: 'TTS', message: 'Synthesizing response chunk 01... Frequency: 24kHz.', type: 'success' },
    { id: 5, time: '14:02:34.42', tag: 'CLAUDE', message: 'Streaming: "The Aegis protocol is currently operating at peak efficiency..."', type: 'success' },
    { id: 6, time: '14:02:35.02', tag: 'ERROR', message: 'WebSocket frame dropped: ERR_CONN_RESET at index 0xFF4A', type: 'error' },
    { id: 7, time: '14:02:35.10', tag: 'SYSTEM', message: 'Auto-recovery: Re-establishing link to synthetic_gateway_v4...', type: 'success' },
    { id: 8, time: '14:02:36.00', tag: 'STT', message: 'Silence detected. Closing audio gate.', type: 'success' },
]

// ─────────────────────────────────────────────
// INTERNAL SUB-COMPONENTS
// ─────────────────────────────────────────────

function TopBar({ activeTab, onTabChange }) {
    return (
        <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-[#0e0e13]/80 backdrop-blur-2xl border-b border-[#00d4ff]/15">
            <div className="flex items-center gap-8">
                <span className="text-xl font-black text-[#00d4ff] drop-shadow-[0_0_8px_rgba(0,212,255,0.5)] font-headline tracking-[0.1em] uppercase">
                    SYNTHETIC_INTEL_v4.2
                </span>
                <nav className="hidden md:flex gap-6">
                    {TABS.map(tab => (
                        <button
                            key={tab}
                            onClick={() => onTabChange(tab)}
                            className={`font-label tracking-[0.1em] uppercase text-sm transition-all duration-300 pb-1 ${activeTab === tab
                                    ? 'text-primary border-b-2 border-primary'
                                    : 'text-primary/50 hover:text-primary hover:bg-primary/10 px-1'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </nav>
            </div>
            <div className="flex items-center gap-4">
                <div className="bg-surface-container-highest px-3 py-1.5 border-b-2 border-primary-dim flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary-dim text-sm">search</span>
                    <input
                        className="bg-transparent border-none outline-none focus:ring-0 text-xs font-label uppercase tracking-widest text-primary w-48 placeholder:text-primary/30"
                        placeholder="QUERY_SYSTEM..."
                    />
                </div>
                <button className="material-symbols-outlined text-primary hover:bg-primary/10 p-2 transition-all">settings</button>
                <button className="material-symbols-outlined text-primary hover:bg-primary/10 p-2 transition-all">power_settings_new</button>
            </div>
        </header>
    )
}

function SideNav({ activeItem, onItemChange, userAvatar }) {
    return (
        <aside className="fixed left-0 top-16 bottom-0 w-64 z-40 flex flex-col bg-[#131319] border-r border-[#00d4ff]/10">
            <div className="p-6 border-b border-[#00d4ff]/10">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-2 h-2 bg-primary animate-pulse" />
                    <h2 className="font-bold text-primary font-headline text-xs tracking-widest uppercase">NODE_OS</h2>
                </div>
                <p className="font-label text-[10px] tracking-widest text-primary/60 uppercase">CONNECTED // PORT:8080</p>
            </div>
            <nav className="flex-1 py-4">
                {NAV_ITEMS.map(({ id, icon }) => (
                    <button
                        key={id}
                        onClick={() => onItemChange(id)}
                        className={`w-full flex items-center px-6 py-3 transition-all duration-300 ${activeItem === id
                                ? 'text-primary bg-primary/10 border-r-4 border-primary'
                                : 'text-primary/40 hover:bg-[#1f1f26] hover:text-primary'
                            }`}
                    >
                        <span className="material-symbols-outlined mr-4 text-xl">{icon}</span>
                        <span className="font-label text-xs tracking-widest">{id}</span>
                    </button>
                ))}
            </nav>
            <div className="p-6 border-t border-[#00d4ff]/10">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        {userAvatar ? (
                            <img src={userAvatar} alt="Core" className="w-10 h-10 border border-primary/30 object-cover" />
                        ) : (
                            <div className="w-10 h-10 border border-primary/30 bg-surface-container-high flex items-center justify-center">
                                <span className="material-symbols-outlined text-primary text-xl">person</span>
                            </div>
                        )}
                        <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 border-2 border-[#0e0e13]" />
                    </div>
                    <div>
                        <p className="text-[10px] font-label text-primary-dim uppercase tracking-tighter">ADMIN_CORE</p>
                        <p className="text-[8px] font-mono text-on-surface-variant">LVL_04_SECURITY</p>
                    </div>
                </div>
            </div>
        </aside>
    )
}

function HeroPanel({ title, status, latency, buffer, bgImage, cards }) {
    return (
        <div className="relative">
            <div className="absolute top-0 left-0 w-5 h-5 border-t-2 border-l-2 border-primary z-10" />
            <div className="absolute bottom-0 right-0 w-5 h-5 border-b-2 border-r-2 border-primary z-10" />
            <div className="relative h-[300px] border border-outline-variant/15 flex flex-col justify-end p-8 overflow-hidden bg-[#25252d]/40 backdrop-blur-[40px] group">
                {bgImage && (
                    <img
                        src={bgImage}
                        alt=""
                        className="absolute inset-0 w-full h-full object-cover opacity-20 mix-blend-overlay group-hover:scale-105 transition-transform duration-1000"
                    />
                )}
                <h1 className="font-headline text-5xl font-extrabold text-primary uppercase tracking-tighter leading-none mb-4 relative z-10">
                    {title}
                </h1>
                <div className="flex gap-4 items-center relative z-10">
                    <div className="bg-primary/20 px-3 py-1 border-l-4 border-primary">
                        <span className="font-label text-xs font-bold tracking-widest text-on-surface">{status}</span>
                    </div>
                    <span className="text-on-surface-variant font-mono text-xs">
                        LATENCY: {latency} // BUFFER: {buffer}
                    </span>
                </div>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-6">
                {cards.map(card => (
                    <div
                        key={card.id}
                        className="bg-surface-container-low p-4 relative cursor-pointer hover:bg-surface-container-high transition-colors"
                    >
                        <span className="text-[8px] font-label text-primary opacity-50 absolute top-2 right-2">{card.id}</span>
                        <span className="material-symbols-outlined text-primary mb-2 block">{card.icon}</span>
                        <h3 className="font-headline text-sm font-bold uppercase mb-1 text-on-surface">{card.label}</h3>
                        <p className="text-xs text-on-surface-variant leading-relaxed">{card.description}</p>
                    </div>
                ))}
            </div>
        </div>
    )
}

function TelemetryPanel({ stats, encryptionKey, onFlush }) {
    return (
        <div className="space-y-6">
            <div className="bg-surface-container border border-outline-variant/15 p-5">
                <h4 className="font-headline text-xs font-bold uppercase mb-4 text-primary tracking-widest flex items-center justify-between">
                    System Stats
                    <span className="material-symbols-outlined text-xs">expand_less</span>
                </h4>
                <div className="space-y-4">
                    {stats.map(stat => (
                        <div key={stat.label}>
                            <div className="flex justify-between text-[10px] mb-1 font-mono uppercase text-on-surface">
                                <span>{stat.label}</span>
                                <span>{stat.value}%</span>
                            </div>
                            <div className="h-1 bg-surface-variant w-full">
                                <div
                                    className={`h-full ${stat.color} transition-all duration-500`}
                                    style={{ width: `${stat.value}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
            <div className="bg-[#131319] border-l-2 border-primary p-4">
                <p className="text-[10px] font-mono text-on-surface-variant mb-2 uppercase">Last_Encryption_Key</p>
                <p className="text-xs font-mono text-primary break-all">{encryptionKey}</p>
            </div>
            <button
                onClick={onFlush}
                className="w-full bg-primary-container text-on-primary-container py-3 font-headline font-black uppercase tracking-widest text-sm hover:brightness-110 hover:shadow-[0_0_15px_#00c3eb] transition-all active:scale-95"
            >
                INITIATE_CORE_FLUSH
            </button>
        </div>
    )
}

function TerminalConsole({ logs, isOpen, onClose, fps, cpu, jsHeap, socketActive }) {
    const [activeTab, setActiveTab] = useState('Events')
    const [paused, setPaused] = useState(false)
    const bottomRef = useRef(null)

    useEffect(() => {
        if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [logs, paused])

    if (!isOpen) return null

    return (
        <section className="fixed bottom-0 left-0 right-0 h-[409px] bg-[#0d1117] border-t border-primary/20 z-[60] flex flex-col shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
            {/* Handle Bar */}
            <div className="h-8 w-full flex items-center justify-between px-4 bg-[#161b22] border-b border-white/5 cursor-row-resize hover:bg-[#1f242c] transition-colors select-none">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-on-surface-variant text-sm">terminal</span>
                    <span className="text-[10px] font-label font-bold text-on-surface-variant uppercase tracking-widest">
                        SYS_DEBUG_CONSOLE v4.2.0
                    </span>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex gap-1">
                        {[0, 1, 2].map(i => <div key={i} className="w-1 h-1 bg-on-surface-variant/30 rounded-full" />)}
                    </div>
                    <button onClick={onClose} className="material-symbols-outlined text-on-surface-variant text-sm hover:text-white">
                        close
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center px-4 bg-[#0d1117] border-b border-white/5">
                {CONSOLE_TABS.map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-6 py-3 text-[10px] font-label font-bold uppercase tracking-widest transition-all ${activeTab === tab
                                ? 'text-primary border-b-2 border-primary'
                                : 'text-on-surface-variant hover:text-primary'
                            }`}
                    >
                        {tab}
                    </button>
                ))}
                <div className="ml-auto flex items-center gap-3">
                    <button
                        onClick={() => setPaused(p => !p)}
                        className="flex items-center gap-2 bg-[#1f242c] px-3 py-1 text-[9px] font-label font-bold uppercase tracking-tighter text-on-surface-variant hover:text-white border border-white/10"
                    >
                        <span className="material-symbols-outlined text-[14px]">{paused ? 'play_circle' : 'pause_circle'}</span>
                        {paused ? 'RESUME' : 'PAUSE'}
                    </button>
                    <button className="flex items-center gap-2 bg-[#1f242c] px-3 py-1 text-[9px] font-label font-bold uppercase tracking-tighter text-on-surface-variant hover:text-white border border-white/10">
                        <span className="material-symbols-outlined text-[14px]">delete</span>
                        CLEAR
                    </button>
                </div>
            </div>

            {/* Log Output */}
            <div
                className="flex-1 bg-black p-4 font-mono text-[11px] overflow-y-auto leading-relaxed selection:bg-primary/30"
                style={{ scrollbarWidth: 'thin', scrollbarColor: '#00d2fd33 transparent' }}
            >
                {logs.map(log => (
                    <div key={log.id} className="flex gap-3 mb-1">
                        <span className="text-on-surface-variant/50 flex-shrink-0">[{log.time}]</span>
                        <span className={`${TAG_COLORS[log.tag] ?? 'text-gray-400'} flex-shrink-0`}>[{log.tag}]</span>
                        <span className={log.type === 'error' ? 'text-red-300' : 'text-green-400'}>{log.message}</span>
                    </div>
                ))}
                <div className="mt-2"><span className="text-green-400 animate-pulse">_</span></div>
                <div ref={bottomRef} />
            </div>

            {/* Status Footer */}
            <div className="h-6 bg-[#0d1117] border-t border-white/5 flex items-center px-4 justify-between">
                <div className="flex gap-4">
                    <span className="text-[8px] font-mono text-on-surface-variant">FPS: {fps.toFixed(1)}</span>
                    <span className="text-[8px] font-mono text-on-surface-variant">CPU: {cpu}</span>
                    <span className="text-[8px] font-mono text-on-surface-variant">JS_HEAP: {jsHeap}</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${socketActive ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className={`text-[8px] font-mono uppercase ${socketActive ? 'text-green-500' : 'text-red-500'}`}>
                        {socketActive ? 'Live: Socket Active' : 'Disconnected'}
                    </span>
                </div>
            </div>
        </section>
    )
}

// ─────────────────────────────────────────────
// ROOT EXPORT — Full Dashboard Page
// ─────────────────────────────────────────────
/**
 * DebugConsole.jsx — Complete SYNTHETIC_INTEL dashboard
 *
 * Props (all optional — defaults built-in):
 *   heroTitle       string
 *   heroStatus      string
 *   heroLatency     string
 *   heroBuffer      string
 *   heroBgImage     string
 *   heroCards       Array<{ id, icon, label, description }>
 *   stats           Array<{ label, value, color }>
 *   encryptionKey   string
 *   logs            Array<{ id, time, tag, message, type }>
 *   fps             number
 *   cpu             string
 *   jsHeap          string
 *   socketActive    boolean
 *   userAvatar      string
 *   onFlush         () => void
 */
export default function DebugConsole({
    heroTitle = 'Neural_Bridge.exe',
    heroStatus = 'LINK_ACTIVE',
    heroLatency = '12ms',
    heroBuffer = '102%',
    heroBgImage,
    heroCards = DEFAULT_CARDS,
    stats = DEFAULT_STATS,
    encryptionKey = 'X99-ALPHA-042-SYNTH-4481-KJ92',
    logs = DEFAULT_LOGS,
    fps = 60.0,
    cpu = '4.2ms',
    jsHeap = '42MB',
    socketActive = true,
    userAvatar,
    onFlush,
}) {
    const [activeTab, setActiveTab] = useState('TERMINAL')
    const [activeNavItem, setActiveNavItem] = useState('SYSLOG')
    const [consoleOpen, setConsoleOpen] = useState(true)

    return (
        <div
            className="relative w-full h-screen overflow-hidden bg-[#0e0e13] font-body text-on-background"
            style={{
                backgroundImage:
                    'linear-gradient(to right,rgba(72,71,77,0.05) 1px,transparent 1px),linear-gradient(to bottom,rgba(72,71,77,0.05) 1px,transparent 1px)',
                backgroundSize: '20px 20px',
            }}
        >
            <TopBar activeTab={activeTab} onTabChange={setActiveTab} />

            <SideNav
                activeItem={activeNavItem}
                onItemChange={setActiveNavItem}
                userAvatar={userAvatar}
            />

            <main
                className="pl-64 pt-16 h-full flex flex-col overflow-hidden"
                style={{ paddingBottom: consoleOpen ? '409px' : '0' }}
            >
                <div className="flex-1 p-8 grid grid-cols-12 gap-6 items-start overflow-auto">
                    <div className="col-span-8">
                        <HeroPanel
                            title={heroTitle}
                            status={heroStatus}
                            latency={heroLatency}
                            buffer={heroBuffer}
                            bgImage={heroBgImage}
                            cards={heroCards}
                        />
                    </div>
                    <div className="col-span-4">
                        <TelemetryPanel
                            stats={stats}
                            encryptionKey={encryptionKey}
                            onFlush={onFlush}
                        />
                    </div>
                </div>
            </main>

            <TerminalConsole
                logs={logs}
                isOpen={consoleOpen}
                onClose={() => setConsoleOpen(false)}
                fps={fps}
                cpu={cpu}
                jsHeap={jsHeap}
                socketActive={socketActive}
            />

            {!consoleOpen && (
                <button
                    onClick={() => setConsoleOpen(true)}
                    className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 bg-[#161b22] border border-primary/20 px-4 py-2 text-[10px] font-label text-primary uppercase tracking-widest hover:bg-[#1f242c] transition-all"
                >
                    <span className="material-symbols-outlined text-sm">terminal</span>
                    SYS_DEBUG_CONSOLE
                </button>
            )}
        </div>
    )
}