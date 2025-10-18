import { useState } from 'react'
import { api, persistAuthToken } from '../lib/api'

export default function Auth() {
  const [tab, setTab] = useState<'employer' | 'candidate'>('employer')

  // Employer
  const [company, setCompany] = useState('MyLink HR')
  const [email, setEmail] = useState('hr@example.com')
  const [password, setPassword] = useState('test1234')
  const [msg, setMsg] = useState('')

  const registerEmployer = async () => {
    const r = await api.post('/employers/register', { company_name: company, email, password })
    persistAuthToken(r.data.access_token)
    setMsg('Регистрация успешна. Токен сохранён.')
  }
  const loginEmployer = async () => {
    const r = await api.post('/auth/login', { email, password })
    persistAuthToken(r.data.access_token)
    setMsg('Вход выполнен. Токен сохранён.')
  }

  // Candidate
  const [fullName, setFullName] = useState('Иван Иванов')
  const [cEmail, setCEmail] = useState('ivan@example.com')
  const [city, setCity] = useState('Алматы')
  const [resume, setResume] = useState('Опыт Python, FastAPI, PostgreSQL...')
  const [createdId, setCreatedId] = useState<string>('')

  const createCandidate = async () => {
    const r = await api.post('/candidates', { full_name: fullName, email: cEmail, city, resume_text: resume })
    setCreatedId(r.data.id)
    setMsg('Резюме создано.')
  }

  return (
    <div className="container py-8">
      <h1 className="text-[28px] leading-[36px] font-semibold mb-4">Вход и регистрация</h1>
      <div className="tabs" role="tablist">
        <button className={`tab ${tab === 'employer' ? 'active' : ''}`} onClick={() => setTab('employer')}>Работодатель</button>
        <button className={`tab ${tab === 'candidate' ? 'active' : ''}`} onClick={() => setTab('candidate')}>Соискатель</button>
      </div>

      {tab === 'employer' && (
        <section className="card p-4 mt-4 space-y-3">
          <h2 className="text-lg font-semibold">Работодатель</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input className="border rounded px-3 py-2" placeholder="Компания" value={company} onChange={e => setCompany(e.target.value)} />
            <input className="border rounded px-3 py-2" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
            <input className="border rounded px-3 py-2" placeholder="Пароль" type="password" value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={registerEmployer}>Регистрация</button>
            <button className="btn-outline" onClick={loginEmployer}>Войти</button>
          </div>
          {msg && <div className="text-sm text-grayx-600">{msg}</div>}
        </section>
      )}

      {tab === 'candidate' && (
        <section className="card p-4 mt-4 space-y-3">
          <h2 className="text-lg font-semibold">Соискатель</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input className="border rounded px-3 py-2" placeholder="ФИО" value={fullName} onChange={e => setFullName(e.target.value)} />
            <input className="border rounded px-3 py-2" placeholder="Email" value={cEmail} onChange={e => setCEmail(e.target.value)} />
            <input className="border rounded px-3 py-2" placeholder="Город" value={city} onChange={e => setCity(e.target.value)} />
            <textarea className="border rounded px-3 py-2 md:col-span-2 min-h-28" placeholder="Текст резюме" value={resume} onChange={e => setResume(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={createCandidate}>Создать резюме</button>
          </div>
          {createdId && <div className="text-sm text-grayx-600">ID резюме: {createdId}</div>}
          {msg && <div className="text-sm text-grayx-600">{msg}</div>}
        </section>
      )}
    </div>
  )
}
