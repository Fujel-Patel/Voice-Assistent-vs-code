import { useState } from 'react'
import { motion } from 'framer-motion'

/**
 * Voice Enrollment.jsx — Voice enrollment flow screen (Image 2)
 * Props:
 *   currentStep: 1 | 2 | 3
 *   phrase: string
 *   elapsed: number (seconds)
 *   total: number (seconds)
 *   profileStrength: number (0-100)
 *   neuralMatch: number
 *   waveformData: number[] (bar heights 0-1)
 *   onReRecord: () => void
 *   onNextStep: () => void
 */

const STEPS = [
    { num: '01', label: 'Read Phrase 1' },
    { num: '02', label: 'Read Phrase 2' },
    { num: '03', label: 'Read Phrase 3' },
]

const DEFAULT_WAVEFORM = [0.3, 0.6, 1.0, 0.5, 0.85, 0.4]

function pad(n) { return String(n).padStart(2, '0') }
function formatTime(secs) { return `${pad(Math.floor(secs / 60))}:${pad(secs % 60)}` }

export default function VoiceEnrollment({
    currentStep = 1,
    phrase = 'Jarvis, activate all systems',
    elapsed = 5,
    total = 10,
    profileStrength = 72,
    neuralMatch = 0.9928,
    waveformData = DEFAULT_WAVEFORM,
    onReRecord,
    onNextStep,
}) {
    const [isRecording] = useState(true)

    const strengthLabel =
        profileStrength >= 90 ? 'EXCELLENT' :
            profileStrength >= 70 ? 'GOOD' :
                profileStrength >= 50 ? 'FAIR' : 'WEAK'

    return (
        <div className="min-h-screen flex flex-col items-center bg-[#0a0a0f] font-body text-on-background relative"
            style={{
                backgroundImage:
                    'linear-gradient(rgba(11,232,255,0.03) 1px,transparent 1px), linear-gradient(90deg,rgba(11,232,255,0.03) 1px,transparent 1px)',
                backgroundSize: '20px 20px',
            }}
        >

            {/* Top Nav */}
            <header className="fixed top-0 w-full flex justify-between items-center px-6 py-4 backdrop-blur-xl z-50">
                <span className="font-headline font-black text-primary tracking-tighter text-xl">SYNTH_AI_OS</span>
                <div className="flex gap-2">
                    {['settings', 'sensors', 'terminal'].map(icon => (
                        <button key={icon} className="material-symbols-outlined text-primary hover:bg-primary/10 transition-all p-2">
                            {icon}
                        </button>
                    ))}
                </div>
            </header>

            {/* Main Card */}
            <main className="w-full max-w-[600px] relative z-10 mt-20 px-4 pb-8">
                {/* Ambient telemetry text */}
                <div className="absolute -top-10 -left-2 opacity-20 font-label text-[10px] tracking-widest text-primary uppercase leading-relaxed">
                    SEC_04 // ADMIN<br />CORE_PROTOCOL_ACTIVE<br />NODE_ID: 882.UX.0
                </div>

                <div className="bg-[#131319]/80 backdrop-blur-2xl border border-primary/15 p-8 relative overflow-hidden"
                    style={{ clipPath: 'polygon(0 0, 95% 0, 100% 5%, 100% 100%, 5% 100%, 0 95%)' }}
                >
                    {/* Dot grid underlay */}
                    <div className="absolute inset-0 opacity-5 pointer-events-none"
                        style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #6dddff 1px, transparent 0)', backgroundSize: '12px 12px' }}
                    />

                    {/* Header */}
                    <div className="flex flex-col items-center text-center mb-10 relative">
                        <div className="relative mb-6">
                            <div className="bg-surface-container-highest p-4 border border-primary/30">
                                <span className="material-symbols-outlined text-primary text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>mic</span>
                            </div>
                            <div className="absolute -left-8 top-1/2 -translate-y-1/2 w-4 h-8 border-l-2 border-primary/40" />
                            <div className="absolute -right-8 top-1/2 -translate-y-1/2 w-4 h-8 border-r-2 border-primary/40" />
                        </div>
                        <h1 className="font-headline font-black text-3xl tracking-[0.2em] text-primary mb-2 uppercase">Voice Enrollment</h1>
                        <p className="font-label text-sm tracking-widest text-on-surface-variant uppercase">Train Jarvis to recognize your voice</p>
                    </div>

                    {/* Step Indicator */}
                    <div className="flex justify-between items-center mb-12 relative px-4">
                        <div className="absolute top-5 left-12 right-12 h-px bg-outline-variant/30" />
                        {STEPS.map((step, i) => {
                            const stepNum = i + 1
                            const isActive = stepNum === currentStep
                            const isDone = stepNum < currentStep
                            return (
                                <div key={step.num} className="relative z-10 flex flex-col items-center gap-2">
                                    <div className={`w-10 h-10 flex items-center justify-center font-black text-xs transition-all ${isActive
                                            ? 'bg-primary text-on-primary shadow-[0_0_15px_rgba(109,221,255,0.4)]'
                                            : isDone
                                                ? 'bg-primary/30 text-primary border border-primary/50'
                                                : 'bg-surface-container-highest border border-outline-variant text-outline'
                                        }`}>
                                        {isDone ? '✓' : step.num}
                                    </div>
                                    <span className={`font-label text-[9px] tracking-tighter uppercase ${isActive ? 'text-primary font-bold' : 'text-outline'}`}>
                                        {step.label}
                                    </span>
                                </div>
                            )
                        })}
                    </div>

                    {/* Recording Area */}
                    <div className="flex flex-col items-center mb-12">
                        <div className="relative w-48 h-48 flex items-center justify-center mb-8">
                            {/* Spinning rings */}
                            <div className="absolute inset-0 border border-primary/10 rounded-full animate-spin" style={{ animationDuration: '8s' }} />
                            <div className="absolute inset-4 border border-dashed border-primary/5 rounded-full" style={{ animation: 'spin 12s linear infinite reverse' }} />
                            {/* Pulse ring */}
                            <motion.div
                                className="w-32 h-32 rounded-full border-2 border-primary flex items-center justify-center bg-primary/5"
                                animate={isRecording ? {
                                    boxShadow: ['0 0 0 0 rgba(109,221,255,0.7)', '0 0 0 20px rgba(109,221,255,0)', '0 0 0 0 rgba(109,221,255,0)'],
                                } : {}}
                                transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
                            >
                                <span className="material-symbols-outlined text-primary text-4xl">keyboard_voice</span>
                            </motion.div>
                        </div>

                        {/* Phrase display */}
                        <div className="text-center space-y-4 w-full">
                            <div className="bg-surface-container-highest/50 p-4 border-l-2 border-primary">
                                <p className="font-headline text-xl tracking-wide text-on-surface">Say: "{phrase}"</p>
                            </div>
                            <div className="font-label text-primary text-lg tracking-[0.3em] font-mono">
                                {formatTime(elapsed)} / {formatTime(total)}
                            </div>
                        </div>
                    </div>

                    {/* Voice Profile Strength */}
                    <div className="space-y-3 mb-10">
                        <div className="flex justify-between items-end">
                            <span className="font-label text-[10px] tracking-widest text-on-surface-variant uppercase">Voice Profile Strength</span>
                            <span className="font-label text-[10px] tracking-widest text-primary uppercase font-bold">
                                {profileStrength}% — {strengthLabel}
                            </span>
                        </div>
                        <div className="h-1.5 w-full bg-surface-container-highest relative overflow-hidden">
                            <motion.div
                                className="absolute top-0 left-0 h-full bg-primary shadow-[0_0_15px_rgba(109,221,255,0.4)]"
                                initial={{ width: 0 }}
                                animate={{ width: `${profileStrength}%` }}
                                transition={{ duration: 0.8, ease: 'easeOut' }}
                            />
                            {/* Tech notches */}
                            <div className="absolute inset-0 flex justify-between px-1 pointer-events-none">
                                {[0, 1, 2, 3, 4].map(i => <div key={i} className="w-px h-full bg-[#0e0e13]/20" />)}
                            </div>
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-4">
                        <button
                            onClick={onReRecord}
                            className="flex-1 py-4 border border-primary/40 text-primary font-headline text-xs tracking-[0.2em] uppercase hover:bg-primary/10 transition-all active:scale-95"
                        >
                            Re-record
                        </button>
                        <button
                            onClick={onNextStep}
                            className="flex-1 py-4 bg-primary text-on-primary font-headline text-xs tracking-[0.2em] font-black uppercase hover:brightness-110 shadow-[0_0_15px_rgba(109,221,255,0.4)] transition-all active:scale-95"
                        >
                            Next Step
                        </button>
                    </div>

                    {/* Coordinate tag */}
                    <div className="absolute bottom-2 right-4 font-label text-[8px] text-outline-variant opacity-50">
                        LAT: 34.0522 // LONG: -118.2437
                    </div>
                </div>

                {/* Info Alert */}
                <div className="mt-8 flex items-start gap-4 p-4 bg-primary-container/10 border-l-2 border-primary-container">
                    <span className="material-symbols-outlined text-primary-container text-[18px] flex-shrink-0">info</span>
                    <p className="text-[11px] font-label text-primary-fixed-dim tracking-wide leading-relaxed uppercase">
                        Ensure you are in a quiet environment. Ambient noise levels exceeding 20dB may interfere with neural voice mapping accuracy.
                    </p>
                </div>
            </main>

            {/* Floating Telemetry (desktop only) */}
            <div className="hidden lg:block fixed right-10 top-1/4 space-y-6 w-48 opacity-40 pointer-events-none">
                <div className="bg-surface-container p-3 border-t border-primary/20">
                    <div className="font-label text-[9px] text-primary mb-2 uppercase">Waveform Analysis</div>
                    <div className="flex items-end gap-1 h-8">
                        {waveformData.map((h, i) => (
                            <motion.div
                                key={i}
                                className="w-1 bg-primary"
                                style={{ height: `${h * 32}px` }}
                                animate={{ height: [`${h * 20}px`, `${h * 32}px`, `${h * 20}px`] }}
                                transition={{ duration: 0.8 + i * 0.1, repeat: Infinity, ease: 'easeInOut' }}
                            />
                        ))}
                    </div>
                </div>
                <div className="bg-surface-container p-3 border-t border-primary/20">
                    <div className="font-label text-[9px] text-primary mb-2 uppercase">Neural Match</div>
                    <div className="font-headline text-lg text-primary tracking-tighter">{neuralMatch.toFixed(4)}</div>
                </div>
            </div>

            {/* Bottom decoration */}
            <div className="fixed bottom-6 left-6 flex items-center gap-3">
                <div className="w-1 h-1 bg-primary" />
                <div className="w-8 h-px bg-primary/30" />
                <span className="font-label text-[10px] text-primary/60 tracking-widest uppercase">Encryption Status: Level 5</span>
            </div>

        </div>
    )
}