import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useNotifications } from '../hooks/useNotifications'
import NotificationContainer from '../components/NotificationContainer'
import LoadingSpinner from '../components/LoadingSpinner'
import AnimatedBackground from '../components/AnimatedBackground'
import PageTransition from '../components/PageTransition'

export default function ResumeEditor() {
  // Notifications
  const { notifications, removeNotification, showSuccess, showError } = useNotifications()
  
  const [candidateId, setCandidateId] = useState<string | null>(() => {
    try { return localStorage.getItem('candidate_id') } catch { return null }
  })
  const [profile, setProfile] = useState<any>({
    basics: { full_name: '', email: '', city: '' },
    summary: '',
    skills: [''],
    experience: [{ company: '', title: '', start: '', end: '', description: '' }],
    education: [{ place: '', degree: '', start: '', end: '' }],
    certificates: [{ name: '', issuer: '', year: '' }],
  })
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const load = async () => {
      if (!candidateId) return
      try {
        const r = await api.get(`/candidates/${candidateId}/profile`)
        setProfile(r.data)
      } catch {}
    }
    load()
  }, [candidateId])

  const save = async () => {
    if (!candidateId) { 
      showError('Ошибка сохранения', 'Сначала загрузите резюме PDF или откликнитесь в каталоге')
      return 
    }
    setBusy(true)
    try {
      await api.put(`/candidates/${candidateId}/profile`, profile)
      showSuccess('Профиль сохранён', 'Ваш профиль успешно обновлён')
    } catch (e: any) {
      console.error('Save profile error:', e)
      showError('Ошибка сохранения', 'Не удалось сохранить профиль. Попробуйте снова.')
    } finally { 
      setBusy(false) 
    }
  }

  const uploadPdf = async () => {
    if (!pdfFile) { 
      showError('Ошибка загрузки', 'Выберите PDF файл')
      return 
    }
    if (!profile.basics.full_name || !profile.basics.email) { 
      showError('Ошибка валидации', 'Заполните ФИО и Email')
      return 
    }
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', pdfFile)
      form.append('full_name', profile.basics.full_name)
      form.append('email', profile.basics.email)
      form.append('city', profile.basics.city || '')
      const r = await api.post('/candidates/upload_pdf', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      const id = r.data.id as string
      setCandidateId(id)
      try { localStorage.setItem('candidate_id', id) } catch {}
      showSuccess('PDF загружен!', 'Резюме успешно обработано через OCR. Теперь заполните профиль вручную для точной оценки.')
    } catch (e: any) {
      console.error('PDF upload error:', e)
      if (e.response?.status === 400) {
        showError('Ошибка загрузки', e.response.data?.detail || 'Некорректный формат файла')
      } else if (e.response?.status === 413) {
        showError('Файл слишком большой', 'Размер файла превышает допустимый лимит')
      } else {
        showError('Ошибка загрузки', 'Загрузка не удалась. Проверьте подключение к интернету.')
      }
    } finally { 
      setBusy(false) 
    }
  }

  return (
    <div className="relative min-h-screen">
      {/* Animated Background */}
      <AnimatedBackground />
      
      {/* Notifications */}
      <NotificationContainer 
        notifications={notifications} 
        onRemove={removeNotification} 
      />
      
      <PageTransition>
        <div className="container py-6 space-y-4 relative z-10">
          <h1 className="text-[28px] leading-[36px] font-semibold">Страница резюме</h1>

          {/* Basics */}
          <section className="card p-4 space-y-2">
            <h2 className="text-lg font-semibold">Основное</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <input className="border rounded px-3 py-2" placeholder="ФИО" value={profile.basics.full_name} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, full_name: e.target.value } })} />
              <input className="border rounded px-3 py-2" placeholder="Email" value={profile.basics.email} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, email: e.target.value } })} />
              <input className="border rounded px-3 py-2" placeholder="Город" value={profile.basics.city} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, city: e.target.value } })} />
            </div>
            <textarea className="border rounded px-3 py-2" placeholder="Кратко о себе" value={profile.summary} onChange={e => setProfile({ ...profile, summary: e.target.value })} />
            <div className="flex items-center gap-2">
              <input type="file" accept="application/pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)} />
              <button className="btn-outline flex items-center gap-2" onClick={uploadPdf} disabled={busy}>
                {busy ? <LoadingSpinner size="sm" /> : null}
                {busy ? 'Загрузка...' : 'Загрузить PDF'}
              </button>
            </div>
          </section>

          {/* Skills */}
          <section className="card p-4 space-y-2">
            <h2 className="text-lg font-semibold">Навыки</h2>
            {profile.skills.map((skill: string, i: number) => (
              <input key={i} className="border rounded px-3 py-2" placeholder="Навык" value={skill} onChange={e => setProfile({ ...profile, skills: profile.skills.map((s: string, j: number) => j === i ? e.target.value : s) })} />
            ))}
            <button className="btn-outline" onClick={() => setProfile({ ...profile, skills: [...profile.skills, ''] })}>Добавить навык</button>
          </section>

          {/* Experience */}
          <section className="card p-4 space-y-2">
            <h2 className="text-lg font-semibold">Опыт работы</h2>
            {profile.experience.map((exp: any, i: number) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <input className="border rounded px-3 py-2" placeholder="Компания" value={exp.company} onChange={e => setProfile({ ...profile, experience: profile.experience.map((ex: any, j: number) => j === i ? { ...ex, company: e.target.value } : ex) })} />
                <input className="border rounded px-3 py-2" placeholder="Должность" value={exp.title} onChange={e => setProfile({ ...profile, experience: profile.experience.map((ex: any, j: number) => j === i ? { ...ex, title: e.target.value } : ex) })} />
                <input className="border rounded px-3 py-2" placeholder="Начало" value={exp.start} onChange={e => setProfile({ ...profile, experience: profile.experience.map((ex: any, j: number) => j === i ? { ...ex, start: e.target.value } : ex) })} />
                <input className="border rounded px-3 py-2" placeholder="Конец" value={exp.end} onChange={e => setProfile({ ...profile, experience: profile.experience.map((ex: any, j: number) => j === i ? { ...ex, end: e.target.value } : ex) })} />
                <textarea className="border rounded px-3 py-2 md:col-span-2" placeholder="Описание" value={exp.description} onChange={e => setProfile({ ...profile, experience: profile.experience.map((ex: any, j: number) => j === i ? { ...ex, description: e.target.value } : ex) })} />
              </div>
            ))}
            <button className="btn-outline" onClick={() => setProfile({ ...profile, experience: [...profile.experience, { company: '', title: '', start: '', end: '', description: '' }] })}>Добавить опыт</button>
          </section>

          {/* Education */}
          <section className="card p-4 space-y-2">
            <h2 className="text-lg font-semibold">Образование</h2>
            {profile.education.map((edu: any, i: number) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <input className="border rounded px-3 py-2" placeholder="Учебное заведение" value={edu.place} onChange={e => setProfile({ ...profile, education: profile.education.map((ed: any, j: number) => j === i ? { ...ed, place: e.target.value } : ed) })} />
                <input className="border rounded px-3 py-2" placeholder="Степень" value={edu.degree} onChange={e => setProfile({ ...profile, education: profile.education.map((ed: any, j: number) => j === i ? { ...ed, degree: e.target.value } : ed) })} />
                <input className="border rounded px-3 py-2" placeholder="Начало" value={edu.start} onChange={e => setProfile({ ...profile, education: profile.education.map((ed: any, j: number) => j === i ? { ...ed, start: e.target.value } : ed) })} />
                <input className="border rounded px-3 py-2" placeholder="Конец" value={edu.end} onChange={e => setProfile({ ...profile, education: profile.education.map((ed: any, j: number) => j === i ? { ...ed, end: e.target.value } : ed) })} />
              </div>
            ))}
            <button className="btn-outline" onClick={() => setProfile({ ...profile, education: [...profile.education, { place: '', degree: '', start: '', end: '' }] })}>Добавить образование</button>
          </section>

          {/* Certificates */}
          <section className="card p-4 space-y-2">
            <h2 className="text-lg font-semibold">Сертификаты</h2>
            {profile.certificates.map((cert: any, i: number) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <input className="border rounded px-3 py-2" placeholder="Название" value={cert.name} onChange={e => setProfile({ ...profile, certificates: profile.certificates.map((c: any, j: number) => j === i ? { ...c, name: e.target.value } : c) })} />
                <input className="border rounded px-3 py-2" placeholder="Организация" value={cert.issuer} onChange={e => setProfile({ ...profile, certificates: profile.certificates.map((c: any, j: number) => j === i ? { ...c, issuer: e.target.value } : c) })} />
                <input className="border rounded px-3 py-2" placeholder="Год" value={cert.year} onChange={e => setProfile({ ...profile, certificates: profile.certificates.map((c: any, j: number) => j === i ? { ...c, year: e.target.value } : c) })} />
              </div>
            ))}
            <button className="btn-outline" onClick={() => setProfile({ ...profile, certificates: [...profile.certificates, { name: '', issuer: '', year: '' }] })}>Добавить сертификат</button>
          </section>

          <div className="flex gap-2">
            <button className="btn-primary flex items-center gap-2" onClick={save} disabled={busy}>
              {busy ? <LoadingSpinner size="sm" /> : null}
              {busy ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>
      </PageTransition>
    </div>
  )
}