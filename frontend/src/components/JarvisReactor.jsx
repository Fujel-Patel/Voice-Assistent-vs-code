import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * JARVIS ARC REACTOR COMPONENT
 * A high-fidelity 3D visualizer that reacts to voice states and audio levels.
 */

const STATE_CONFIG = {
  IDLE: {
    coreColor: '#00d2ff',
    ringColor: '#00a2ff',
    rotationSpeed: 0.2,
    pulseFreq: 1.2,
    pulseAmp: 0.05,
    glowIntensity: 0.6,
  },
  LISTENING: {
    coreColor: '#00ffff',
    ringColor: '#00f5ff',
    rotationSpeed: 1.2,
    pulseFreq: 4.5,
    pulseAmp: 0.15,
    glowIntensity: 1.8,
  },
  THINKING: {
    coreColor: '#ffffff',
    ringColor: '#3b82f6',
    rotationSpeed: 3.5,
    pulseFreq: 0.8,
    pulseAmp: 0.02,
    glowIntensity: 1.2,
  },
  SPEAKING: {
    coreColor: '#3b82f6',
    ringColor: '#60a5fa',
    rotationSpeed: 0.6,
    pulseFreq: 2.5,
    pulseAmp: 0.25,
    glowIntensity: 1.4,
  },
  ERROR: {
    coreColor: '#ef4444',
    ringColor: '#f87171',
    rotationSpeed: 0.1,
    pulseFreq: 0.5,
    pulseAmp: 0.1,
    glowIntensity: 0.8,
  }
}

export default function JarvisReactor({ state = 'IDLE', audioLevel = 0 }) {
  const groupRef = useRef()
  const coreRef = useRef()
  const ring1Ref = useRef()
  const ring2Ref = useRef()
  const ring3Ref = useRef()
  const particlesRef = useRef()

  const config = useMemo(() => {
    const s = state?.toUpperCase()
    if (s === 'LISTENING' || s === 'WAKE_DETECTED') return STATE_CONFIG.LISTENING
    if (s === 'THINKING' || s === 'TRANSCRIBING') return STATE_CONFIG.THINKING
    if (s === 'SPEAKING') return STATE_CONFIG.SPEAKING
    if (s === 'ERROR') return STATE_CONFIG.ERROR
    return STATE_CONFIG.IDLE
  }, [state])

  // Particles setup
  const particlesCount = 120
  const [positions, scales] = useMemo(() => {
    const pos = new Float32Array(particlesCount * 3)
    const sc = new Float32Array(particlesCount)
    for (let i = 0; i < particlesCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / particlesCount)
      const theta = Math.sqrt(particlesCount * Math.PI) * phi
      
      const r = 2.2 + ((i * 567.89) % 1) * 0.5
      pos[i * 3] = r * Math.cos(theta) * Math.sin(phi)
      pos[i * 3 + 1] = r * Math.sin(theta) * Math.sin(phi)
      pos[i * 3 + 2] = r * Math.cos(phi)
      
      sc[i] = ((i * 987.65) % 1)
    }
    return [pos, sc]
  }, [particlesCount])

  useFrame((stateFrame, delta) => {
    const t = stateFrame.clock.elapsedTime
    const level = Math.max(0, Math.min(1, Number(audioLevel) || 0))
    const pulse = 1 + Math.sin(t * config.pulseFreq) * config.pulseAmp + level * 0.4

    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.1
      groupRef.current.rotation.x = Math.sin(t * 0.5) * 0.05
    }

    if (coreRef.current) {
      coreRef.current.scale.setScalar(pulse)
      coreRef.current.material.emissiveIntensity = config.glowIntensity + level * 5
    }

    if (ring1Ref.current) {
      ring1Ref.current.rotation.z += delta * config.rotationSpeed
      ring1Ref.current.rotation.x = Math.PI / 2 + Math.sin(t * 0.2) * 0.1
      ring1Ref.current.scale.setScalar(1 + level * 0.2)
    }

    if (ring2Ref.current) {
      ring2Ref.current.rotation.z -= delta * (config.rotationSpeed * 0.7)
      ring2Ref.current.rotation.y = Math.cos(t * 0.3) * 0.1
      ring2Ref.current.scale.setScalar(1.2 + level * 0.15)
    }

    if (ring3Ref.current) {
      ring3Ref.current.rotation.z += delta * (config.rotationSpeed * 1.5)
      ring3Ref.current.scale.setScalar(0.8 + level * 0.1)
    }

    if (particlesRef.current) {
      particlesRef.current.rotation.y -= delta * 0.05
      particlesRef.current.rotation.z += delta * 0.02
    }
  })

  return (
    <group ref={groupRef}>
      {/* Central Power Core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 64, 64]} />
        <meshStandardMaterial
          color={config.coreColor}
          emissive={config.coreColor}
          emissiveIntensity={config.glowIntensity}
          toneMapped={false}
          roughness={0}
          metalness={1}
        />
      </mesh>

      {/* Primary Arc Ring (Horizontal) */}
      <mesh ref={ring1Ref}>
        <torusGeometry args={[1.6, 0.04, 16, 100]} />
        <meshStandardMaterial
          color={config.ringColor}
          emissive={config.ringColor}
          emissiveIntensity={config.glowIntensity * 2}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Secondary Dynamic Ring (Slightly tilted) */}
      <mesh ref={ring2Ref} rotation={[0.2, 0, 0]}>
        <torusGeometry args={[2.0, 0.02, 16, 80]} />
        <meshStandardMaterial
          color={config.ringColor}
          emissive={config.ringColor}
          emissiveIntensity={config.glowIntensity}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* Inner Accelerator Ring */}
      <mesh ref={ring3Ref}>
        <torusGeometry args={[1.0, 0.06, 16, 60]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive={config.ringColor}
          emissiveIntensity={config.glowIntensity * 3}
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* Support Brackets */}
      {[...Array(8)].map((_, i) => (
        <mesh key={i} rotation={[0, 0, (i / 8) * Math.PI * 2]} position={[0, 0, 0]}>
          <boxGeometry args={[0.1, 1.8, 0.05]} />
          <meshStandardMaterial 
            color="#334155" 
            metalness={1} 
            roughness={0.2} 
            transparent 
            opacity={0.4}
          />
        </mesh>
      ))}

      {/* Energy Particles */}
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={particlesCount}
            array={positions}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-scale"
            count={particlesCount}
            array={scales}
            itemSize={1}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          color={config.ringColor}
          transparent
          opacity={0.4}
          sizeAttenuation
          blending={THREE.AdditiveBlending}
        />
      </points>
      
      {/* Volumetric Core Glow */}
      <mesh scale={[1.2, 1.2, 1.2]}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshStandardMaterial
          color={config.coreColor}
          transparent
          opacity={0.15}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}

