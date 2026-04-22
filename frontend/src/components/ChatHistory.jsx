import { useMemo, useState } from 'react'
import { useAppStore } from '../store/appStore'

export default function ChatHistory({ sendMessage }) {
  const [draft, setDraft] = useState('')
  const messages = useAppStore((state) => state.messages)
  const isChatOpen = useAppStore((state) => state.isChatOpen)
  const toggleChat = useAppStore((state) => state.toggleChat)
  const currentResponse = useAppStore((state) => state.currentResponse)

  const visibleMessages = useMemo(() => messages.slice(-20), [messages])

  const submit = (event) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content) return

    sendMessage({
      type: 'user_command',
      payload: { text: content },
    })
    setDraft('')
  }

  return (
    <section className={`chat-history ${isChatOpen ? 'open' : ''}`}>
      <button type='button' onClick={toggleChat} className='chat-toggle'>
        {isChatOpen ? 'Hide Transcript' : 'Show Transcript'}
      </button>

      {isChatOpen ? (
        <>
          <div className='chat-list'>
            {visibleMessages.map((message) => (
              <article key={message.id} className={`msg ${message.role}`}>
                <h4>{message.role === 'assistant' ? 'Jarvis' : 'You'}</h4>
                <p>{message.content}</p>
              </article>
            ))}
            {currentResponse ? (
              <article className='msg assistant pending'>
                <h4>Jarvis</h4>
                <p>{currentResponse}</p>
              </article>
            ) : null}
          </div>
          <form className='chat-compose' onSubmit={submit}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder='Type command...'
              maxLength={1000}
            />
            <button type='submit'>Send</button>
          </form>
        </>
      ) : null}
    </section>
  )
}
