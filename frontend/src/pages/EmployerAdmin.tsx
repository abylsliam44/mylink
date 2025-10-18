import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

export default function EmployerAdmin() {
  // Vacancy form
  const [title, setTitle] = useState('Python Developer')
  const [description, setDescription] = useState('FastAPI, PostgreSQL, Docker. Офис Алматы, EN B2.')
  const [location, setLocation] = useState('Алматы')
  const [salaryMin, setSalaryMin] = useState<number | ''>(600000)
  const [salaryMax, setSalaryMax] = useState<number | ''>(900000)
  const [stack, setStack] = useState('python, fastapi, postgresql, docker')

  const [vacancies, setVacancies] = useState<any[]>([])
  const [activeVacancyId, setActiveVacancyId] = useState<string>('')
  const [responses, setResponses] = useState<any[]>([])

  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [minMatch, setMinMatch] = useState<number>(0)

  const loadVacancies = async () => {
    const r = await api.get('/vacancies')
    setVacancies(r.data)
    if (r.data.length && !activeVacancyId) setActiveVacancyId(r.data[0].id)
  }
  const createVacancy = async () => {
    await api.post('/vacancies', {
      title,
      description,
      location,
      salary_min: salaryMin === '' ? null : salaryMin,
      salary_max: salaryMax === '' ? null : salaryMax,
      requirements: { stack: stack.split(',').map(s => s.trim().toLowerCase()).filter(Boolean) }
    })
    await loadVacancies()
  }
  const loadResponses = async (vacancyId: string) => {
    const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
    setResponses(r.data)
  }

  useEffect(() => { loadVacancies().catch(() => {}) }, [])
  useEffect(() => { if (activeVacancyId) loadResponses(activeVacancyId).catch(() => {}) }, [activeVacancyId])

  const filtered = useMemo(() => {
    return responses.filter(r => {
      const byStatus = statusFilter === 'all' ? true : r.status === statusFilter
      const score = typeof r.relevance_score === 'number' ? Math.round(r.relevance_score * 100) : 0
      return byStatus && score >= minMatch
    })
  }, [responses, statusFilter, minMatch])

  // Aggregates for charts
  const stats = useMemo(() => {
    const total = filtered.length
    const passed = filtered.filter(r => (r.relevance_score || 0) >= 0.75).length
    const borderline = filtered.filter(r => (r.relevance_score || 0) >= 0.6 && (r.relevance_score || 0) < 0.75).length
    const failed = total - passed - borderline
    const avg = total ? Math.round((filtered.reduce((a, r) => a + (r.relevance_score || 0), 0) / total) * 100) : 0
    return { total, passed, borderline, failed, avg }
  }, [filtered])

  const chartData = useMemo(() => (
    [
      { name: 'Подходят', value: stats.passed, color: '#12B76A' },
      { name: 'Сомнительно', value: stats.borderline, color: '#F79009' },
      { name: 'Не подходят', value: stats.failed, color: '#EF4444' },
    ]
  ), [stats])

  const dailyData = useMemo(() => {
    // группировка по дате создания
    const byDate: Record<string, number> = {}
    filtered.forEach(r => {
      const d = (r.created_at || '').slice(0, 10)
      byDate[d] = (byDate[d] || 0) + 1
    })
    return Object.entries(byDate).map(([date, count]) => ({ date, count }))
  }, [filtered])

  const runPipeline = async (vacancyId: string, candidateId: string, responseId: string) => {
    await api.post('/ai/pipeline/screen_by_ids', { vacancy_id: vacancyId, candidate_id: candidateId, response_id: responseId, limits: { max_questions: 3 } })
    await loadResponses(vacancyId)
  }

  return (
    <div className="container py-6 space-y-6">
      {/* KPIs */}
      <section className="card p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
          <div className="p-3 rounded border border-grayx-300"><div className="text-xs text-grayx-600">Всего откликов</div><div className="text-[20px] font-semibold">{stats.total}</div></div>
          <div className="p-3 rounded border border-grayx-300"><div className="text-xs text-grayx-600">Средний матч</div><div className="text-[20px] font-semibold">{stats.avg}%</div></div>
          <div className="p-3 rounded border border-grayx-300"><div className="text-xs text-grayx-600">Подходят</div><div className="text-[20px] font-semibold text-success-600">{stats.passed}</div></div>
          <div className="p-3 rounded border border-grayx-300"><div className="text-xs text-grayx-600">Сомнительно / Не подходят</div><div className="text-[20px] font-semibold">{stats.borderline} / {stats.failed}</div></div>
        </div>
      </section>

      {/* Create vacancy */}
      <section className="card p-4 space-y-3">
        <h2 className="text-lg font-semibold">Опубликовать вакансию</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border rounded px-3 py-2" placeholder="Название" value={title} onChange={e => setTitle(e.target.value)} />
          <input className="border rounded px-3 py-2" placeholder="Город / формат" value={location} onChange={e => setLocation(e.target.value)} />
          <textarea className="border rounded px-3 py-2 md:col-span-2 min-h-28" placeholder="Описание" value={description} onChange={e => setDescription(e.target.value)} />
          <div className="flex gap-2">
            <input className="border rounded px-3 py-2" type="number" placeholder="Зарплата мин" value={salaryMin} onChange={e => setSalaryMin(e.target.value === '' ? '' : Number(e.target.value))} />
            <input className="border rounded px-3 py-2" type="number" placeholder="Зарплата макс" value={salaryMax} onChange={e => setSalaryMax(e.target.value === '' ? '' : Number(e.target.value))} />
          </div>
          <input className="border rounded px-3 py-2 md:col-span-2" placeholder="Стек (через запятую)" value={stack} onChange={e => setStack(e.target.value)} />
        </div>
        <div>
          <button className="btn-primary" onClick={createVacancy}>Опубликовать</button>
        </div>
      </section>

      {/* Vacancies list */}
      <section className="card p-4 space-y-3">
        <h2 className="text-lg font-semibold">Мои вакансии</h2>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-grayx-600">
                <th className="py-2 pr-2">Название</th>
                <th className="py-2 pr-2">Город</th>
                <th className="py-2 pr-2">Зарплата</th>
                <th className="py-2 pr-2">Действия</th>
              </tr>
            </thead>
            <tbody>
              {vacancies.map(v => (
                <tr key={v.id} className={activeVacancyId === v.id ? 'bg-grayx-50' : ''}>
                  <td className="py-2 pr-2 font-medium">{v.title}</td>
                  <td className="py-2 pr-2">{v.location}</td>
                  <td className="py-2 pr-2">{[v.salary_min, v.salary_max].filter(Boolean).join('—') || '—'}</td>
                  <td className="py-2 pr-2">
                    <button className="btn-outline" onClick={() => setActiveVacancyId(v.id)}>Отклики</button>
                  </td>
                </tr>
              ))}
              {vacancies.length === 0 && (
                <tr><td className="py-3 text-grayx-600" colSpan={4}>Нет вакансий</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Responses & analytics */}
      {activeVacancyId && (
        <section className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Отклики</h2>
            <div className="flex items-center gap-3">
              <select className="border rounded px-2 py-2 text-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="all">Все статусы</option>
                <option value="new">new</option>
                <option value="in_chat">in_chat</option>
                <option value="approved">approved</option>
                <option value="rejected">rejected</option>
              </select>
              <label className="text-sm text-grayx-600">Мин. Match {minMatch}%</label>
              <input type="range" min={0} max={100} value={minMatch} onChange={e => setMinMatch(Number(e.target.value))} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={chartData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={4}>
                    {chartData.map((e, i) => (<Cell key={i} fill={e.color} />))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyData}>
                  <XAxis dataKey="date" hide={dailyData.length > 12} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2E6BFF" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-grayx-600">
                  <th className="py-2 pr-2">Кандидат</th>
                  <th className="py-2 pr-2">Город</th>
                  <th className="py-2 pr-2">Статус</th>
                  <th className="py-2 pr-2">Match %</th>
                  <th className="py-2 pr-2">Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => (
                  <tr key={r.id}>
                    <td className="py-2 pr-2 font-medium">{r.candidate_name}</td>
                    <td className="py-2 pr-2">{r.candidate_city}</td>
                    <td className="py-2 pr-2">{r.status}</td>
                    <td className="py-2 pr-2">{typeof r.relevance_score === 'number' ? Math.round(r.relevance_score * 100) : '—'}%</td>
                    <td className="py-2 pr-2 flex gap-2">
                      <button className="btn-outline" onClick={() => runPipeline(activeVacancyId, r.candidate_id, r.id)}>Запустить ИИ</button>
                      {r.rejection_reasons && <details className="border rounded p-2"><summary className="cursor-pointer">Сводка</summary><pre className="text-xs overflow-auto max-h-64">{JSON.stringify(r.rejection_reasons, null, 2)}</pre></details>}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td className="py-3 text-grayx-600" colSpan={5}>Нет откликов под фильтр</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
