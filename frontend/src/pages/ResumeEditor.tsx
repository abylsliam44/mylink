import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useNotifications } from '../hooks/useNotifications'
import NotificationContainer from '../components/NotificationContainer'
import LoadingSpinner from '../components/LoadingSpinner'
import AnimatedBackground from '../components/AnimatedBackground'
import PageTransition from '../components/PageTransition'
import PDFUploadZone from '../components/PDFUploadZone'
import SkillsInput from '../components/SkillsInput'
import ExperienceInput from '../components/ExperienceInput'
import EducationInput from '../components/EducationInput'
import CertificatesInput from '../components/CertificatesInput'

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
        <div className="container py-6 space-y-8 relative z-10">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Моё резюме</h1>
            <p className="text-gray-600">Заполните информацию о себе для точного анализа</p>
          </div>

          {/* PDF Upload Section */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Загрузка PDF резюме</h2>
            <PDFUploadZone
              onFileSelect={setPdfFile}
              onUpload={uploadPdf}
              isUploading={busy}
              selectedFile={pdfFile}
            />
          </section>

          {/* Basic Information */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Основная информация</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">ФИО *</label>
                <input
                  type="text"
                  value={profile.basics.full_name}
                  onChange={e => setProfile({ ...profile, basics: { ...profile.basics, full_name: e.target.value } })}
                  placeholder="Иванов Иван Иванович"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email *</label>
                <input
                  type="email"
                  value={profile.basics.email}
                  onChange={e => setProfile({ ...profile, basics: { ...profile.basics, email: e.target.value } })}
                  placeholder="ivan@example.com"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Город</label>
                <input
                  type="text"
                  value={profile.basics.city}
                  onChange={e => setProfile({ ...profile, basics: { ...profile.basics, city: e.target.value } })}
                  placeholder="Алматы"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">О себе</label>
              <textarea
                value={profile.summary}
                onChange={e => setProfile({ ...profile, summary: e.target.value })}
                placeholder="Кратко расскажите о себе, ваших целях и достижениях"
                rows={4}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
              />
            </div>
          </section>

          {/* Skills */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <SkillsInput
              skills={profile.skills}
              onChange={(skills) => setProfile({ ...profile, skills })}
            />
          </section>

          {/* Experience */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <ExperienceInput
              experiences={profile.experience}
              onChange={(experiences) => setProfile({ ...profile, experience: experiences })}
            />
          </section>

          {/* Education */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <EducationInput
              educations={profile.education}
              onChange={(educations) => setProfile({ ...profile, education: educations })}
            />
          </section>

          {/* Certificates */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <CertificatesInput
              certificates={profile.certificates}
              onChange={(certificates) => setProfile({ ...profile, certificates })}
            />
          </section>

          {/* Save Button */}
          <div className="flex justify-center">
            <button 
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-lg font-medium"
              onClick={save} 
              disabled={busy}
            >
              {busy ? <LoadingSpinner size="sm" /> : null}
              {busy ? 'Сохранение...' : 'Сохранить профиль'}
            </button>
          </div>
        </div>
      </PageTransition>
    </div>
  )
}