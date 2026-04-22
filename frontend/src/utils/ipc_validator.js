export function validateIpcEnvelope(message) {
  if (!message || typeof message !== 'object' || Array.isArray(message)) {
    return { valid: false, error: 'Message must be an object' }
  }

  if (typeof message.type !== 'string' || !message.type.trim()) {
    return { valid: false, error: "Field 'type' must be a non-empty string" }
  }

  if (!message.payload || typeof message.payload !== 'object' || Array.isArray(message.payload)) {
    return { valid: false, error: "Field 'payload' must be an object" }
  }

  return { valid: true }
}
