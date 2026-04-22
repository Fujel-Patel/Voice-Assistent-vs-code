import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import VoiceStateArc from '../components/home/VoiceStateArc'

describe('VoiceStateArc', () => {
  it('renders listening label for listening state', () => {
    render(<VoiceStateArc state='listening' audioLevel={0.3} />)
    expect(screen.getByText('● LISTENING')).toBeTruthy()
  })

  it('renders speaking label for speaking state', () => {
    render(<VoiceStateArc state='speaking' audioLevel={0.8} />)
    expect(screen.getByText('◎ SPEAKING')).toBeTruthy()
  })
})
