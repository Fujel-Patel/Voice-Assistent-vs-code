export function sanitizeAssistantText(input) {
  let candidate = String(input || '').trim()
  if (!candidate) return ''

  const fenced = candidate.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i)
  if (fenced?.[1]) {
    candidate = fenced[1].trim()
  }

  const extractEmbeddedObject = (text) => {
    const fencedBlockMatches = [...text.matchAll(/```(?:json)?\s*([\s\S]*?)\s*```/gi)]
      .map((match) => (match?.[1] || '').trim())
      .filter(Boolean)

    for (const block of fencedBlockMatches) {
      try {
        const parsed = JSON.parse(block)
        if (parsed && typeof parsed === 'object') {
          return parsed
        }
      } catch {
        // continue
      }
    }

    for (let i = 0; i < text.length; i += 1) {
      if (text[i] !== '{') continue
      try {
        const parsed = JSON.parse(text.slice(i))
        if (parsed && typeof parsed === 'object') {
          return parsed
        }
      } catch {
        // continue
      }
    }

    return null
  }

  for (let i = 0; i < 2; i += 1) {
    try {
      const parsed = JSON.parse(candidate)
      if (typeof parsed === 'string') {
        candidate = parsed.trim()
        continue
      }
      if (parsed && typeof parsed === 'object') {
        const nested = parsed.response || parsed.text || ''
        if (nested) {
          candidate = String(nested).trim()
          continue
        }
      }
      break
    } catch {
      const embedded = extractEmbeddedObject(candidate)
      if (embedded) {
        const nested = embedded.response || embedded.text || ''
        if (nested) {
          candidate = String(nested).trim()
        }
      }
      break
    }
  }

  const improveReadability = (text) => String(text || '')
    .replace(/([,.;!?])(?=\S)/g, '$1 ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\bIam\b/g, 'I am')
    .replace(/\bIam(?=[a-z])/g, 'I am ')
    .replace(/\bHowmay\b/g, 'How may')
    .replace(/\bHowcan\b/g, 'How can')
    .replace(/\bIassist\b/g, 'I assist')
    .replace(/\bIassistyou\b/g, 'I assist you')
    .replace(/\bassistyou\b/g, 'assist you')
    .replace(/\s+/g, ' ')
    .trim()

  return improveReadability(candidate)
}
