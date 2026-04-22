import { useCallback, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { BACKEND_WS_URL, WS_STATES } from '../utils/constants'
import { validateIpcEnvelope } from '../utils/ipc_validator'

let sharedSocket = null
let sharedReconnectTimer = null
let sharedHeartbeatTimer = null
let sharedConnectTimeout = null
let sharedReconnectAttempts = 0
let sharedConsumers = 0
const sharedSubscriptions = new Map()

function dispatchSharedMessage(message) {
  const handlers = sharedSubscriptions.get(message.type)
  if (!handlers?.size) {
    return
  }

  handlers.forEach((handler) => {
    try {
      handler(message.payload, message)
    } catch {
      // Keep dispatch loop resilient even if one subscriber fails.
    }
  })
}

function clearSharedTimers() {
  if (sharedReconnectTimer) {
    clearTimeout(sharedReconnectTimer)
    sharedReconnectTimer = null
  }
  if (sharedHeartbeatTimer) {
    clearInterval(sharedHeartbeatTimer)
    sharedHeartbeatTimer = null
  }
  if (sharedConnectTimeout) {
    clearTimeout(sharedConnectTimeout)
    sharedConnectTimeout = null
  }
}

function scheduleSharedReconnect() {
  clearSharedTimers()
  useAppStore.getState().setConnectionState(WS_STATES.RECONNECTING)

  const delay = Math.min(1000 * 2 ** sharedReconnectAttempts, 30000)
  sharedReconnectAttempts += 1

  sharedReconnectTimer = setTimeout(() => {
    connectSharedSocket()
  }, delay)
}

function startSharedHeartbeat() {
  if (sharedHeartbeatTimer) {
    clearInterval(sharedHeartbeatTimer)
  }

  sharedHeartbeatTimer = setInterval(() => {
    if (sharedSocket?.readyState === WebSocket.OPEN) {
      sharedSocket.send(
        JSON.stringify({
          type: 'ping',
          payload: {},
          timestamp: new Date().toISOString(),
          request_id: `ping-${Date.now()}`,
        }),
      )
    }
  }, 30000)
}

function connectSharedSocket() {
  if (sharedSocket && (sharedSocket.readyState === WebSocket.OPEN || sharedSocket.readyState === WebSocket.CONNECTING)) {
    return
  }

  useAppStore.getState().setConnectionState(WS_STATES.CONNECTING)

  const ws = new WebSocket(BACKEND_WS_URL)
  sharedSocket = ws

  ws.onopen = () => {
    if (sharedConnectTimeout) {
      clearTimeout(sharedConnectTimeout)
      sharedConnectTimeout = null
    }
    sharedReconnectAttempts = 0
    useAppStore.getState().setConnectionState(WS_STATES.CONNECTED)
    startSharedHeartbeat()
  }

  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data)
      const validation = validateIpcEnvelope(parsed)
      if (!validation.valid) {
        return
      }
      dispatchSharedMessage(parsed)
    } catch {
      // Ignore malformed messages.
    }
  }

  ws.onclose = () => {
    if (sharedConnectTimeout) {
      clearTimeout(sharedConnectTimeout)
      sharedConnectTimeout = null
    }
    useAppStore.getState().setConnectionState(WS_STATES.DISCONNECTED)
    sharedSocket = null
    if (sharedConsumers > 0) {
      scheduleSharedReconnect()
    }
  }

  ws.onerror = () => {
    if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
      try {
        ws.close()
      } catch {
        // Ignore close race conditions.
      }
    }
    useAppStore.getState().addToast({
      type: 'warning',
      title: 'Connection issue',
      message: 'Attempting reconnect to backend...',
    })
  }

  sharedConnectTimeout = setTimeout(() => {
    if (ws.readyState === WebSocket.CONNECTING) {
      useAppStore.getState().setConnectionState(WS_STATES.DISCONNECTED)
      try {
        ws.close()
      } catch {
        // Ignore close race conditions.
      }
    }
  }, 5000)
}

function disconnectSharedSocket() {
  clearSharedTimers()
  sharedReconnectAttempts = 0

  if (sharedSocket) {
    const socket = sharedSocket
    if (socket.readyState === WebSocket.CONNECTING) {
      socket.onopen = () => socket.close()
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
    } else {
      socket.onclose = null
      socket.close()
    }
    sharedSocket = null
  }

  useAppStore.getState().setConnectionState(WS_STATES.DISCONNECTED)
}

export function useWebSocket() {
  const connectionState = useAppStore((state) => state.connectionState)

  const subscribe = useCallback((eventType, handler) => {
    if (!sharedSubscriptions.has(eventType)) {
      sharedSubscriptions.set(eventType, new Set())
    }
    sharedSubscriptions.get(eventType).add(handler)

    return () => {
      const handlers = sharedSubscriptions.get(eventType)
      if (!handlers) return
      handlers.delete(handler)
      if (!handlers.size) {
        sharedSubscriptions.delete(eventType)
      }
    }
  }, [])

  const connect = useCallback(() => {
    connectSharedSocket()
  }, [])

  const disconnect = useCallback(() => {
    disconnectSharedSocket()
  }, [])

  const sendMessage = useCallback((message) => {
    if (sharedSocket?.readyState !== WebSocket.OPEN) {
      return false
    }

    const envelope = {
      timestamp: new Date().toISOString(),
      request_id: message.request_id || `${Date.now()}-${Math.random()}`,
      ...message,
    }

    sharedSocket.send(JSON.stringify(envelope))
    return true
  }, [])

  useEffect(() => {
    sharedConsumers += 1
    connectSharedSocket()

    return () => {
      sharedConsumers = Math.max(0, sharedConsumers - 1)
      if (sharedConsumers === 0) {
        disconnectSharedSocket()
      }
    }
  }, [connect, disconnect])

  return {
    sendMessage,
    subscribe,
    connectionState,
    reconnect: connect,
  }
}
