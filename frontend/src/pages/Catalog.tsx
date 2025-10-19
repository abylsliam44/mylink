import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'

type Vacancy = {
  id: string
  title: string
  description: string
  requirements?: { stack?: string[] }
  location: string
  salary_min?: number | null
  salary_max?: number | null
  created_at?: string
}

export default function Catalog() {
  // Data
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [selectedVacancyId, setSelectedVacancyId] = useState<string>('')

  // Candidate (client-side state)
  const [candidateId, setCandidateId] = useState<string | null>(() => {
    try { return localStorage.getItem('candidate_id') } catch { return null }
  })
  const [fullName, setFullName] = useState<string>(() => {
    try { return localStorage.getItem('candidate_name') || '' } catch { return '' }
  })
  const [email, setEmail] = useState<string>(() => {
    try { return localStorage.getItem('candidate_email') || '' } catch { return '' }
  })
  const [city, setCity] = useState<string>(() => {
    try { return localStorage.getItem('candidate_city') || '' } catch { return '' }
  })
  const [resumeSnippet, setResumeSnippet] = useState<string>(() => {
    try { return localStorage.getItem('candidate_resume_snippet') || '' } catch { return '' }
  })

  // Upload & apply
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string>('')
  const [err, setErr] = useState<string>('')

  // Search UI
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<'new' | 'top' | 'almaty'>('new')
  const [showResumeEditor, setShowResumeEditor] = useState(false)

  // Load vacancies
  useEffect(() => {
    api.get('/vacancies/public')
      .then(r => setVacancies(r.data))
      .catch(() => setVacancies([]))
  }, [])

  useEffect(() => {
    if (!selectedVacancyId && vacancies.length) setSelectedVacancyId(vacancies[0].id)
  }, [vacancies, selectedVacancyId])

  const filtered = useMemo(() => {
    let list = vacancies
    if (tab === 'almaty') list = list.filter(v => (v.location || '').toLowerCase().includes('алматы') || (v.location || '').toLowerCase().includes('almaty'))
    if (tab === 'top') list = list.slice().sort((a, b) => (b.salary_max || 0) - (a.salary_max || 0))
    if (query.trim()) {
      const q = query.toLowerCase()
      list = list.filter(v => [v.title, v.location, (v.requirements?.stack || []).join(' ')].some(t => (t || '').toLowerCase().includes(q)))
    }
    return list
  }, [vacancies, tab, query])

  const selectedVacancy = filtered.find(v => v.id === selectedVacancyId) || filtered[0]

  // Upload PDF -> create candidate and store id
  const uploadResume = async () => {
    if (!pdfFile) {
      setErr('Выберите PDF‑файл')
      return
    }
    if (!fullName || !email) {
      setErr('Заполните ФИО и E‑mail')
      return
    }
    setBusy(true); setErr(''); setMsg('')
    try {
      const form = new FormData()
      form.append('file', pdfFile)
      form.append('full_name', fullName)
      form.append('email', email)
      form.append('city', city)
      const res = await api.post('/candidates/upload_pdf', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      const id = res.data.id as string
      setCandidateId(id)
      try {
        localStorage.setItem('candidate_id', id)
        localStorage.setItem('candidate_name', fullName)
        localStorage.setItem('candidate_email', email)
        localStorage.setItem('candidate_city', city)
        const snippet = (res.data.resume_text || '').slice(0, 400)
        localStorage.setItem('candidate_resume_snippet', snippet)
        setResumeSnippet(snippet)
      } catch {}
      setMsg('Резюме загружено и сохранено')
    } catch (e: any) {
      setErr('Не удалось загрузить PDF. Попробуйте ещё раз.')
    } finally {
      setBusy(false)
    }
  }

  // Apply with existing candidateId, or create lightweight profile
  const apply = async () => {
    if (!selectedVacancy) return
    setBusy(true); setErr(''); setMsg('')
    try {
      let cid = candidateId
      if (!cid) {
        if (!fullName || !email) {
          setErr('Укажите ФИО и E‑mail или загрузите резюме PDF')
          setBusy(false)
          return
        }
        const c = await api.post('/candidates', { full_name: fullName, email, city: city || '—', resume_text: resumeSnippet || '' })
        cid = c.data.id
        setCandidateId(cid)
        try { localStorage.setItem('candidate_id', cid as string) } catch {}
      }
      await api.post('/responses', { candidate_id: cid, vacancy_id: selectedVacancy.id })
      setMsg('Спасибо! Отклик отправлен')
    } catch (e: any) {
      setErr('Не удалось отправить отклик. Попробуйте ещё раз.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {/* Filters */}
      {/* Filter bar (static, not sticky) */}
      <section className="bg-white border-b border-[#E6E8EB]">
        <div className="container py-4">
          <div className="w-full flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 border border-[#E6E8EB] rounded-xl px-3 py-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M21 21l-4.3-4.3" stroke="#98A2B3" strokeWidth="2" strokeLinecap="round"/><circle cx="11" cy="11" r="7" stroke="#98A2B3" strokeWidth="2"/></svg>
                <input className="flex-1 outline-none" aria-label="Поиск" placeholder="Поиск по вакансии, навыкам, городу" value={query} onChange={e => setQuery(e.target.value)} />
                <button className="btn-primary">Найти</button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className={`tab ${tab === 'new' ? 'active' : ''}`} onClick={() => setTab('new')}>Новые вакансии</button>
              <button className={`tab ${tab === 'top' ? 'active' : ''}`} onClick={() => setTab('top')}>Топ зарплаты</button>
              <button className={`tab ${tab === 'almaty' ? 'active' : ''}`} onClick={() => setTab('almaty')}>Работа в Алматы</button>
            </div>
          </div>
        </div>
      </section>

      {/* Grid */}
      <div className="container py-6">
        <div className="grid-cols-preview">
          {/* Left: vacancies list */}
          <div className="space-y-3">
            {filtered.map(v => (
              <div key={v.id} className={`card p-4 hover:border-primary-600 ${selectedVacancy?.id === v.id ? 'border-primary-600' : ''}`} onClick={() => setSelectedVacancyId(v.id)} role="button" aria-label={`Открыть вакансию ${v.title}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-[18px] leading-[24px] font-semibold text-grayx-900">{v.title}</div>
                    <div className="text-[14px] leading-[20px] text-grayx-600">{v.location}</div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="badge">{[v.salary_min, v.salary_max].filter(Boolean).join(' — ') || 'З/п не указана'}</span>
                  {(v.requirements?.stack || []).slice(0, 4).map((s, i) => (<span key={i} className="badge">{s}</span>))}
                </div>
                <div className="mt-3 flex items-center justify-between text-[12px] leading-[18px] text-grayx-600">
                  <span>Опубликовано {formatDays(v.created_at)} назад</span>
                  <a className="link" href="#">ПРЕДПРОСМОТР</a>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="text-sm text-grayx-600">Нет вакансий по вашему запросу</div>
            )}
          </div>

          {/* Right: resume + apply */}
          <div className="space-y-4 sticky" style={{ top: 16 }}>
            {/* My Resume (collapsed by default) */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[16px] font-semibold text-grayx-900">Моё резюме</h3>
                {!showResumeEditor && !candidateId && (
                  <button className="btn-outline" onClick={() => setShowResumeEditor(true)}>Заполнить</button>
                )}
              </div>
              {!candidateId && !showResumeEditor && (
                <div className="text-[12px] text-[#666]">Добавьте резюме позже или загрузите PDF — форма спрятана, чтобы не мешать.</div>
              )}
              {(!candidateId && showResumeEditor) && (
                <div className="space-y-2">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <input className="border rounded px-3 py-2" placeholder="ФИО" value={fullName} onChange={e => setFullName(e.target.value)} />
                    <input className="border rounded px-3 py-2" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
                    <input className="border rounded px-3 py-2" placeholder="Город" value={city} onChange={e => setCity(e.target.value)} />
                    <input className="border rounded px-3 py-2" type="file" accept="application/pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)} />
                  </div>
                  <div className="mt-1 flex gap-2">
                    <button className="btn-primary" onClick={uploadResume} disabled={busy}>Загрузить PDF</button>
                    <button className="btn-outline" onClick={() => { setPdfFile(null); setResumeSnippet(''); setCandidateId(null); try { localStorage.removeItem('candidate_id'); localStorage.removeItem('candidate_resume_snippet') } catch {} }}>Очистить</button>
                    <button className="btn-outline" onClick={() => setShowResumeEditor(false)}>Скрыть</button>
                  </div>
                </div>
              )}
              {candidateId && (
                <div className="text-[12px] text-grayx-600">Резюме загружено. ID: {candidateId}</div>
              )}
              {resumeSnippet && (
                <div className="mt-3 text-[12px] text-grayx-600 max-h-40 overflow-auto border rounded p-2 bg-grayx-50">{resumeSnippet}</div>
              )}
            </div>

            {/* Apply */}
            <div className="card p-4">
              <h3 className="text-[16px] font-semibold text-grayx-900 mb-2">Отклик на вакансию</h3>
              <div className="text-[12px] text-grayx-600 mb-2">Вакансия: <b>{selectedVacancy?.title || '—'}</b> ({selectedVacancy?.location || '—'})</div>
              <div className="flex gap-2">
                <button className="btn-primary" onClick={apply} disabled={busy || !selectedVacancy}>Откликнуться</button>
                <button className="btn-outline" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>К списку</button>
              </div>
              {msg && <div className="text-sm text-success-600 mt-2">{msg}</div>}
              {err && <div className="text-sm text-danger-600 mt-2">{err}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatDays(created?: string) {
  if (!created) return 'недавно'
  try {
    const d = new Date(created)
    const diff = Math.max(0, Date.now() - d.getTime())
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return days === 0 ? 'сегодня' : `${days} дн.`
  } catch {
    return 'недавно'
  }
}

