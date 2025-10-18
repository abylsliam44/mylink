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

  // Apply (одна кнопка) + PDF
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [applied, setApplied] = useState<string>('')
  const [error, setError] = useState<string>('')

  // UI
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<'new' | 'top' | 'almaty'>('new')

  // Load vacancies
  useEffect(() => {
    api.get('/vacancies').then(r => setVacancies(r.data)).catch(() => setVacancies([]))
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

  // One-click apply: без формы — только PDF опционально. Если PDF не загружен — создаём минимальную карточку кандидата сгенерированным email
  const apply = async () => {
    try {
      setError('')
      setApplied('')
      if (!selectedVacancy) return
      if (pdfFile) {
        const form = new FormData()
        form.append('file', pdfFile)
        form.append('full_name', 'Кандидат')
        form.append('email', `user_${Date.now()}@example.com`)
        form.append('city', '')
        form.append('vacancy_id', selectedVacancy.id)
        await api.post('/candidates/upload_pdf', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      } else {
        const c = await api.post('/candidates', { full_name: 'Кандидат', email: `user_${Date.now()}@example.com`, city: '', resume_text: '' })
        await api.post('/responses', { candidate_id: c.data.id, vacancy_id: selectedVacancy.id })
      }
      setApplied('Спасибо! Отклик отправлен')
      setPdfFile(null)
    } catch (e: any) {
      setError('Не удалось отправить отклик. Попробуйте ещё раз.')
    }
  }

  return (
    <div>
      {/* Hero */}
      <section className="hero">
        <div className="container text-center">
          <h1 className="text-[44px] leading-[52px] font-semibold tracking-[-0.01em]">Найдите идеальную вакансию</h1>
          <div className="searchbar" role="search" aria-label="Поиск вакансий">
            <input aria-label="Введите название профессии" placeholder="Введите название профессии" value={query} onChange={e => setQuery(e.target.value)} />
            <button aria-label="Найти">НАЙТИ</button>
          </div>
          <div className="tabs" role="tablist" aria-label="Фильтры">
            <button className={`tab ${tab === 'new' ? 'active' : ''}`} role="tab" aria-selected={tab === 'new'} onClick={() => setTab('new')}>Новые вакансии</button>
            <button className={`tab ${tab === 'top' ? 'active' : ''}`} role="tab" aria-selected={tab === 'top'} onClick={() => setTab('top')}>Топ зарплаты</button>
            <button className={`tab ${tab === 'almaty' ? 'active' : ''}`} role="tab" aria-selected={tab === 'almaty'} onClick={() => setTab('almaty')}>Работа в Алматы</button>
          </div>
        </div>
      </section>

      {/* Grid */}
      <div className="container py-6">
        <div className="grid-cols-preview">
          {/* Left: vacancies list */}
          <div className="space-y-3">
            {filtered.map(v => (
              <div key={v.id} className={`card p-4 ${selectedVacancy?.id === v.id ? 'border-primary-600' : ''}`} onClick={() => setSelectedVacancyId(v.id)} role="button" aria-label={`Открыть вакансию ${v.title}`}>
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

          {/* Right: preview + one-click apply */}
          <div className="space-y-4 sticky" style={{ top: 16 }}>
            {/* Preview card */}
            <div className="card p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full" style={{ background: '#F2F4F7' }} />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-grayx-900 font-semibold">{selectedVacancy?.title || 'Вакансия'}</div>
                      <div className="text-grayx-600 text-[14px]">{selectedVacancy?.location}</div>
                    </div>
                    <button className="btn-outline">СТРАНИЦА ВАКАНСИИ</button>
                  </div>
                </div>
              </div>
              <div className="mt-4">
                <h3 className="text-[14px] font-semibold text-grayx-900">Описание</h3>
                <div className="mt-2 text-[12px] text-grayx-600 whitespace-pre-wrap">{selectedVacancy?.description}</div>
              </div>
              <div className="mt-4">
                <h3 className="text-[14px] font-semibold text-grayx-900">Требования</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(selectedVacancy?.requirements?.stack || []).map((s, i) => (<span key={i} className="badge">{s}</span>))}
                </div>
              </div>
            </div>

            {/* One-click apply */}
            <div className="card p-4">
              <h3 className="text-[16px] font-semibold text-grayx-900 mb-2">Отклик одной кнопкой</h3>
              <div className="text-[12px] text-grayx-600 mb-2">Вы можете загрузить PDF‑резюме, или отправить отклик без резюме.</div>
              <input type="file" accept="application/pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)} />
              <div className="mt-3 flex gap-2">
                <button className="btn-primary" onClick={apply} disabled={!selectedVacancy}>Откликнуться</button>
              </div>
              {applied && <div className="text-sm text-success-600 mt-2">{applied}</div>}
              {error && <div className="text-sm text-danger-600 mt-2">{error}</div>}
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

