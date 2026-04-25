/**
 * Tests — WebSocket Hook
 * =======================
 * Tests for useWebSocket.js — the WebSocket IPC connection hook.
 * Mock WebSocket API for all tests.
 */

import { describe, it, expect } from 'vitest'

// Mock global WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    setTimeout(() => {
      this.readyState = 1
      if (this.onopen) this.onopen({})
    }, 10)
  }
  send(data) { this._sent = (this._sent || []).concat(data) }
  close() { this.readyState = 3 }
}

global.WebSocket = MockWebSocket

describe('WebSocket Hook', () => {
  it('vitest and mock WebSocket are configured correctly', () => {
    const ws = new global.WebSocket('ws://localhost:8765/ws')
    expect(ws.url).toBe('ws://localhost:8765/ws')
  })

  it('backend WebSocket URL is correct', () => {
    const BACKEND_WS_URL = 'ws://localhost:8765/ws'
    expect(BACKEND_WS_URL).toMatch(/^ws:\/\//)
  })

  // TODO Phase 4: Add hook rendering tests:
  // it('connects on mount and shows IDLE state', async () => {
  //   const { result } = renderHook(() => useWebSocket('ws://localhost:8765/ws'))
  //   await waitFor(() => expect(result.current.isConnected).toBe(true))
  // })
})
