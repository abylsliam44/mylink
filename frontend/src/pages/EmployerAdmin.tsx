import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import CardKPI from '../components/CardKPI'
import Donut from '../components/Donut'
import BreakdownRow from '../components/BreakdownRow'
import SheetCreateJob from '../components/SheetCreateJob'
import RiskCarousel from '../components/RiskCarousel'

export default function EmployerAdmin() {
  // SheetCreateJob manages its own form; keep ref for smooth scroll if needed later
  // const formRef = useRef<HTMLDivElement | null>(null)

  // Lists
  const [vacancies, setVacancies] = useState<any[]>([])
  const [activeVacancyId, setActiveVacancyId] = useState<string>('')
  const [responses, setResponses] = useState<any[]>([])
  const [selectedResponse, setSelectedResponse] = useState<any | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [minMatch, setMinMatch] = useState<number>(0)

  // Loading/error states
  const [loadingVacancies, setLoadingVacancies] = useState(false)
  const [errorVacancies, setErrorVacancies] = useState<string>('')
  const [loadingResponses, setLoadingResponses] = useState(false)
  const [errorResponses, setErrorResponses] = useState<string>('')
  // legacy create form states removed; handled in SheetCreateJob
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [aiData, setAiData] = useState<any | null>(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [aiCache, setAiCache] = useState<Record<string, any>>({})

  const loadVacancies = async () => {
    setLoadingVacancies(true)
    setErrorVacancies('')
    try {
      const r = await api.get('/vacancies')
      setVacancies(r.data)
      if (r.data.length && !activeVacancyId) setActiveVacancyId(r.data[0].id)
    } catch (e: any) {
      setErrorVacancies(e?.response?.data?.detail || 'Ошибка загрузки вакансий')
    } finally {
      setLoadingVacancies(false)
    }
  }
  // creation handled inside SheetCreateJob
  const loadResponses = async (vacancyId: string) => {
    setLoadingResponses(true)
    setErrorResponses('')
    try {
      const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
      setResponses(r.data)
      if (r.data.length) setSelectedResponse(r.data[0])
    } catch (e: any) {
      setErrorResponses(e?.response?.data?.detail || 'Ошибка загрузки откликов')
    } finally {
      setLoadingResponses(false)
    }
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

  const stats = useMemo(() => {
    const total = filtered.length
    const passed = filtered.filter(r => (r.relevance_score || 0) >= 0.75).length
    const borderline = filtered.filter(r => (r.relevance_score || 0) >= 0.6 && (r.relevance_score || 0) < 0.75).length
    const failed = total - passed - borderline
    const avg = total ? Math.round((filtered.reduce((a, r) => a + (r.relevance_score || 0), 0) / total) * 100) : 0
    return { total, passed, borderline, failed, avg }
  }, [filtered])

  // charts removed in vertical layout; keep only KPI above

  const runPipeline = async (vacancyId: string, candidateId: string, responseId: string) => {
    await api.post('/ai/pipeline/screen_by_ids', { vacancy_id: vacancyId, candidate_id: candidateId, response_id: responseId, limits: { max_questions: 3 } })
    await loadResponses(vacancyId)
  }

  const runPipelineForSelected = async () => {
    if (!selectedResponse) return
    setAiLoading(true)
    setAiError('')
    try {
      const r = await api.post('/ai/pipeline/screen_by_ids', {
        vacancy_id: activeVacancyId,
        candidate_id: selectedResponse.candidate_id,
        response_id: selectedResponse.id,
        limits: { max_questions: 3 }
      })
      setAiData(r.data)
      setAiCache((c) => ({ ...c, [selectedResponse.id]: r.data }))
      // refresh row to pick persisted score
      await loadResponses(activeVacancyId)
    } catch (e: any) {
      setAiError(e?.response?.data?.detail || 'Ошибка работы ИИ')
    } finally {
      setAiLoading(false)
    }
  }

  // Auto-run when selecting response (with cache)
  useEffect(() => {
    if (!selectedResponse) return
    const cached = aiCache[selectedResponse.id]
    if (cached) { setAiData(cached); return }
    runPipelineForSelected().catch(() => {})
  }, [selectedResponse])

  const exportCsv = () => {
    const rows = [['Кандидат', 'Город', 'Статус', 'Match %']]
    filtered.forEach(r => rows.push([r.candidate_name, r.candidate_city, r.status, String(Math.round((r.relevance_score || 0) * 100))]))
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'responses.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="container mx-auto max-w-[1200px] px-4 py-6 space-y-6">
      {/* Hero */}
      <section className="rounded-xl p-5" style={{ background: 'linear-gradient(90deg, #EFF4FF 0%, #F2F4F7 100%)' }}>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-[28px] leading-[36px] font-semibold tracking-[-0.01em] text-grayx-900">Панель работодателя</h1>
            <div className="text-[14px] leading-[20px] text-grayx-600">Публикуйте вакансии, анализируйте отклики и запускайте ИИ‑оценку кандидатов.</div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => setOpenCreate(true)}>Новая вакансия</button>
            <button className="btn-outline" onClick={exportCsv} disabled={!filtered.length}>Экспорт CSV</button>
          </div>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <CardKPI title="Всего откликов" value={stats.total} />
        <CardKPI title="Средний матч" value={`${stats.avg}%`} />
        <CardKPI title="Подходят" value={stats.passed} />
        <CardKPI title="Сомн./Не подходят" value={`${stats.borderline}/${stats.failed}`} />
      </section>

      {/* Create vacancy */}
      <SheetCreateJob open={openCreate} onClose={() => setOpenCreate(false)} onCreated={loadVacancies} />

      {/* Vacancies list */}
      <section className="rounded-2xl border border-[#E6E8EB] bg-white shadow-sm p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-[20px] leading-[28px] font-semibold">Мои вакансии</h2>
          <div className="text-[12px] leading-[18px] text-grayx-600">Всего: {vacancies.length}</div>
        </div>
        {loadingVacancies && <div className="text-[14px] text-[#666]">Загрузка...</div>}
        {errorVacancies && (
          <div className="text-[14px] text-[#DC2626] flex items-center gap-2">
            {errorVacancies}
            <button className="btn-outline" onClick={loadVacancies}>Повторить</button>
          </div>
        )}
        {!loadingVacancies && !errorVacancies && (
        <div className="overflow-auto">
          <table className="w-full text-[14px]">
            <thead>
              <tr className="text-left text-grayx-600 text-[12px]">
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
                <tr><td className="py-3 text-grayx-600" colSpan={4}>Нет вакансий. Создайте первую с помощью кнопки «Новая вакансия».</td></tr>
              )}
            </tbody>
          </table>
        </div>
        )}
      </section>

      {activeVacancyId && (
        <section className="rounded-2xl border border-[#E6E8EB] bg-white shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[20px] leading-[28px] font-semibold">Отклики</h2>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-[12px] leading-[18px]">
                <span className="badge">Статус: {statusFilter === 'all' ? 'все' : statusFilter}</span>
                <span className="badge">Мин. Match: {minMatch}%</span>
              </div>
              <select className="border rounded px-2 py-2 text-[14px]" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="all">Все статусы</option>
                <option value="new">new</option>
                <option value="in_chat">in_chat</option>
                <option value="approved">approved</option>
                <option value="rejected">rejected</option>
              </select>
              <input type="range" min={0} max={100} value={minMatch} onChange={e => setMinMatch(Number(e.target.value))} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left column: responses list as vertical cards */}
            <div className="lg:col-span-7 space-y-3 order-2 lg:order-none">
              {loadingResponses && (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="rounded-2xl border border-[#E6E8EB] bg-white p-4 animate-pulse">
                      <div className="h-4 w-40 bg-[#EEF2FF] rounded mb-2" />
                      <div className="h-3 w-64 bg-[#F1F3F5] rounded" />
                    </div>
                  ))}
                </div>
              )}
              {!loadingResponses && filtered.length === 0 && (
                <div className="rounded-2xl border border-dashed border-[#E6E8EB] bg-white p-8 text-center text-[14px] text-[#666]">Отклики ожидают данные</div>
              )}
              {!loadingResponses && filtered.map(r => (
                <ResponseCard
                  key={r.id}
                  response={r}
                  selected={selectedResponse?.id === r.id}
                  onSelect={() => setSelectedResponse(r)}
                  onRun={() => runPipeline(activeVacancyId, r.candidate_id, r.id)}
                />
              ))}
            </div>

            {/* Right column: AI Analyst */}
            <aside className="lg:col-span-5 order-1 lg:order-none">
              <div className="sticky top-4 rounded-2xl border border-[#E6E8EB] bg-white shadow-sm p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-[16px] font-semibold">AI Analyst</div>
                </div>
                {!selectedResponse && <div className="text-[14px] text-[#666]">Выберите отклик слева. Пока данные ожидаются.</div>}
                {selectedResponse && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Donut value={Math.round(aiData?.scorer?.overall_match_pct ?? (typeof selectedResponse.relevance_score === 'number' ? selectedResponse.relevance_score * 100 : 0))} colorByThresholds={[{max:60,color:'#DC2626'},{min:60,max:75,color:'#F59E0B'},{min:75,color:'#16A34A'}]} />
                      <div className="min-w-0">
                        <div className="text-[14px] text-[#0A0A0A] font-medium truncate">{selectedResponse.candidate_name}</div>
                        <div className="text-[12px] text-[#666] truncate">{selectedResponse.candidate_city}</div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <BreakdownRow label="Навыки" pct={aiData?.scorer?.scores_pct?.skills ?? 0} />
                      <BreakdownRow label="Опыт" pct={aiData?.scorer?.scores_pct?.experience ?? 0} />
                      <BreakdownRow label="Языки" pct={aiData?.scorer?.scores_pct?.langs ?? 0} />
                      <BreakdownRow label="Локация" pct={aiData?.scorer?.scores_pct?.location ?? 0} />
                      <BreakdownRow label="Компенсация" pct={aiData?.scorer?.scores_pct?.comp ?? 0} />
                      <BreakdownRow label="Образование" pct={aiData?.scorer?.scores_pct?.education ?? 0} />
                      <BreakdownRow label="Домен" pct={aiData?.scorer?.scores_pct?.domain ?? 0} />
                    </div>
                    <div className="space-y-2">
                      {aiData?.scorer?.summary?.positives?.length > 0 ? (
                        <div>
                          <div className="text-[12px] text-[#666] mb-1">Что делает кандидата сильным</div>
                          <ul className="list-disc pl-5 text-[13px]">
                            {aiData.scorer.summary.positives.map((s: string, i: number) => (<li key={i}>{s}</li>))}
                          </ul>
                        </div>
                      ) : (
                        <div className="text-[12px] text-[#666]">Сильные стороны ожидают данные</div>
                      )}
                      <div>
                        <div className="text-[12px] text-[#666] mb-1">Зоны роста и риски</div>
                        <RiskCarousel items={aiData?.scorer?.summary?.risks || []} />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <button className="btn-primary col-span-2" onClick={runPipelineForSelected} disabled={aiLoading}>Отправить приглашение</button>
                      <button className="btn-outline" onClick={runPipelineForSelected} disabled={aiLoading}>Уточнить</button>
                    </div>
                    {aiError && <div className="text-[12px] text-[#DC2626]" role="alert" aria-live="polite">{aiError}</div>}
                    <div className="text-[12px] text-[#666]">Обновлено {aiData ? 'только что' : '—'}</div>
                  </div>
                )}
              </div>
            </aside>
          
          </div>

          {loadingResponses && <div className="text-[14px] text-[#666]">Загрузка...</div>}
          {errorResponses && (
            <div className="text-[14px] text-[#DC2626] flex items-center gap-2">
              {errorResponses}
              <button className="btn-outline" onClick={() => loadResponses(activeVacancyId)}>Повторить</button>
            </div>
          )}
          {/* Table view replaced by vertical cards above */}
        </section>
      )}
    </div>
  )
}

function ResponseCard({ response, selected, onSelect, onRun }: { response: any; selected: boolean; onSelect: () => void; onRun: () => void }) {
  const pct = typeof response.relevance_score === 'number' ? Math.round(response.relevance_score * 100) : 0
  const badge = pct >= 75 ? 'bg-[#EAF7EE] text-[#16A34A]' : pct >= 60 ? 'bg-[#FFF7E6] text-[#F59E0B]' : 'bg-[#FDECEC] text-[#DC2626]'
  return (
    <div className={`rounded-2xl border ${selected ? 'border-[#4F46E5]' : 'border-[#E6E8EB]'} bg-white shadow-sm p-4`} onClick={onSelect}>
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <div className="text-[14px] font-medium text-[#0A0A0A] truncate">{response.candidate_name}</div>
          <div className="text-[12px] text-[#666] truncate">{response.candidate_city || '—'}</div>
        </div>
        <div className={`text-[12px] px-2 py-1 rounded-full ${badge}`}>{pct}%</div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button className="btn-outline" onClick={onRun}>Запустить ИИ</button>
        {response.rejection_reasons && (
          <details className="border rounded p-2">
            <summary className="cursor-pointer text-[12px]">Сводка</summary>
            <pre className="text-xs overflow-auto max-h-64">{JSON.stringify(response.rejection_reasons, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

// placeholder (legacy export to satisfy file tail); no-op
 
