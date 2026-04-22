import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'

const MODE_CONFIG = {
  INPUT: {
    color: '#00d4ff', // Jarvis-Blue / Cyan
    rotationSpeed: 0.6,
    pulseFreq: 2.5,
    pulseAmp: 0.08,
    ringA_speed: 1.2,
    ringB_speed: -1.0,
  },
  THINKING: {
    color: '#f59e0b', // Jarvis-Gold (Amber)
    rotationSpeed: 0.2,
    pulseFreq: 0.8,
    pulseAmp: 0.05,
    ringA_speed: -0.5,
    ringB_speed: 0.5,
  },
  OUTPUT: {
    color: '#ffffff', // Jarvis-White/Gold
    rotationSpeed: 0.3,
    pulseFreq: 1.2,
    pulseAmp: 0.15,
    ringA_speed: 0.8,
    ringB_speed: -0.8,
  },
  IDLE: {
    color: '#9ca3af',
    rotationSpeed: 0.3,
    pulseFreq: 1.0,
    pulseAmp: 0.04,
    ringA_speed: 0.5,
    ringB_speed: -0.5,
  },
}

export default function GeminiBlob({ state, audioLevel = 0 }) {
  const groupRef = useRef()
  const coreRef = useRef()
  const ringARef = useRef()
  const ringBRef = useRef()

  const mode = useMemo(() => {
    const s = state?.toUpperCase()
    if (s === 'LISTENING' || s === 'WAKE_DETECTED') return 'INPUT'
    if (s === 'THINKING' || s === 'TRANSCRIBING') return 'THINKING'
    if (s === 'SPEAKING') return 'OUTPUT'
    return 'IDLE'
  }, [state])

  const config = MODE_CONFIG[mode] || MODE_CONFIG.IDLE

  useFrame((frameState, delta) => {
    const t = frameState.clock.elapsedTime
    const level = Math.max(0, Math.min(1, Number(audioLevel) || 0))

    // Base pulse + audio reactivity
    const pulse = 1 + Math.sin(t * config.pulseFreq) * config.pulseAmp + level * (mode === 'OUTPUT' ? 0.25 : 0.15)

    if (groupRef.current) {
      groupRef.current.rotation.y += delta * config.rotationSpeed
      groupRef.current.rotation.x = Math.sin(t * 0.3) * 0.08
    }

    if (coreRef.current) {
      coreRef.current.scale.setScalar(pulse)
      coreRef.current.rotation.x += delta * 0.45
      coreRef.current.rotation.z += delta * 0.25
    }

    if (ringARef.current) {
      ringARef.current.rotation.z += delta * config.ringA_speed
      ringARef.current.scale.setScalar(1 + level * 0.22)
    }

    if (ringBRef.current) {
      ringBRef.current.rotation.x += delta * config.ringB_speed
      ringBRef.current.scale.setScalar(1.02 + level * 0.15)
    }
  })

  return (
    <group ref={groupRef}>
      <mesh ref={coreRef}>
        <icosahedronGeometry args={[1.02, 5]} />
        <meshStandardMaterial
          color={config.color}
          roughness={0.18}
          metalness={0.28}
          emissive={config.color}
          emissiveIntensity={mode === 'OUTPUT' ? 0.6 : 0.35}
        />
      </mesh>
      <mesh ref={ringARef} rotation={[0.4, 0, 0]}>
        <torusGeometry args={[1.46, 0.04, 24, 128]} />
        <meshStandardMaterial color={config.color} roughness={0.3} metalness={0.45} emissive={config.color} emissiveIntensity={0.22} />
      </mesh>
      <mesh ref={ringBRef} rotation={[1.15, 0, 0]}>
        <torusGeometry args={[1.2, 0.03, 18, 96]} />
        <meshStandardMaterial color={config.color} roughness={0.35} metalness={0.4} emissive={config.color} emissiveIntensity={0.15} />
      </mesh>
    </group>
  )
}
