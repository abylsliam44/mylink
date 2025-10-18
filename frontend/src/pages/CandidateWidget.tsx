import { useEffect, useRef, useState } from 'react'
import { api, API_BASE, wsUrl } from '../lib/api'

export default function CandidateWidget() {
  const [fullName, setFullName] = useState('Ivan Ivanov')
  const [email, setEmail] = useState('ivan@example.com')
  const [phone, setPhone] = useState('+79990000000')
  const [city, setCity] = useState('Moscow')
  const [resumeText, setResumeText] = useState('Experienced Python developer...')

  const [candidateId, setCandidateId] = useState<string>('')
  const [vacancyId, setVacancyId] = useState<string>('')
  const [responseId, setResponseId] = useState<string>('')

  const [messages, setMessages] = useState<{ sender: 'bot' | 'me', text: string }[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<number | null>(null)

  const inputCls = 'border rounded px-3 py-2 w-full'
  const btnCls = 'inline-flex items-center gap-2 rounded bg-blue-600 text-white px-3 py-2 text-sm hover:bg-blue-700 disabled:opacity-50'

  const createCandidate = async () => {
    const res = await api.post(`/candidates`, {
      full_name: fullName,
      email,
      phone,
      city,
      resume_text: resumeText,
    })
    setCandidateId(res.data.id)
  }

  const createResponse = async () => {
    if (!candidateId || !vacancyId) return
    const res = await api.post(`/responses`, {
      candidate_id: candidateId,
      vacancy_id: vacancyId,
    })
    setResponseId(res.data.id)
  }

  const scheduleReconnect = () => {
    if (reconnectAttempts.current >= 5) return
    const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempts.current))
    reconnectAttempts.current += 1
    reconnectTimer.current = window.setTimeout(() => connectWs(), delay)
  }

  const connectWs = () => {
    if (!responseId) return
    if (wsRef.current) {
      try { wsRef.current.close() } catch {}
    }
    const url = wsUrl(`/ws/chat/${responseId}`)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      reconnectAttempts.current = 0
      setMessages(prev => [...prev, { sender: 'bot', text: 'Connected. Wait for a question...' }])
    }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'bot_message' && data.message) {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message }])
        } else if (data.type === 'chat_ended') {
          setMessages(prev => [...prev, { sender: 'bot', text: `Chat ended. approved=${String(data.approved)} reason=${data.reason || ''}` }])
        }
      } catch {}
    }
    ws.onclose = () => {
      setMessages(prev => [...prev, { sender: 'bot', text: 'Connection closed.' }])
      scheduleReconnect()
    }
    ws.onerror = () => {
      try { ws.close() } catch {}
    }
  }

  const [input, setInput] = useState('')
  const sendMsg = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const text = input.trim()
    if (!text) return
    ws.send(JSON.stringify({ message: text }))
    setMessages(prev => [...prev, { sender: 'me', text }])
    setInput('')
  }

  useEffect(() => {
    return () => {
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Candidate</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className={inputCls} placeholder="Full name" value={fullName} onChange={e => setFullName(e.target.value)} />
          <input className={inputCls} placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input className={inputCls} placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} />
          <input className={inputCls} placeholder="City" value={city} onChange={e => setCity(e.target.value)} />
          <textarea className={`${inputCls} min-h-24 md:col-span-2`} placeholder="Resume text" value={resumeText} onChange={e => setResumeText(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={createCandidate}>Create Candidate</button>
          {candidateId && <span className="text-sm text-gray-600">Candidate ID: {candidateId}</span>}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Response</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className={inputCls} placeholder="Vacancy ID" value={vacancyId} onChange={e => setVacancyId(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={createResponse} disabled={!candidateId || !vacancyId}>Create Response</button>
          <button className={btnCls} onClick={connectWs} disabled={!responseId}>Connect Chat</button>
          {responseId && <span className="text-sm text-gray-600">Response ID: {responseId}</span>}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Chat</h2>
        <div className="h-64 overflow-auto border rounded p-2 bg-gray-50">
          {messages.map((m, i) => (
            <div key={i} className={m.sender === 'me' ? 'text-right' : 'text-left'}>
              <span className={m.sender === 'me' ? 'inline-block bg-blue-600 text-white px-3 py-1 rounded mb-1' : 'inline-block bg-white border px-3 py-1 rounded mb-1'}>
                {m.text}
              </span>
            </div>
          ))}
          {messages.length === 0 && <div className="text-sm text-gray-500">No messages yet</div>}
        </div>
        <div className="flex gap-2">
          <input className={`${inputCls} flex-1`} placeholder="Type your answer..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' ? sendMsg() : undefined} />
          <button className={btnCls} onClick={sendMsg}>Send</button>
        </div>
      </section>
    </div>
  )
}
