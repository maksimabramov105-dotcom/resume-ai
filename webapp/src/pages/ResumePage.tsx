import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateResume } from '../services/api'
import { useUserStore } from '../stores/userStore'
import { hapticMedium } from '../services/telegram'

export default function ResumePage() {
  const navigate = useNavigate()
  const { user, decrementCredit } = useUserStore()
  const [vacancy, setVacancy] = useState('')
  const [experience, setExperience] = useState('')
  const [education, setEducation] = useState('')
  const [skills, setSkills] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!vacancy.trim() || !experience.trim() || !skills.trim()) {
      setError('Заполни вакансию, опыт и навыки')
      return
    }
    setLoading(true)
    setError('')
    try {
      hapticMedium()
      const { data } = await generateResume({ vacancy_text: vacancy, experience, education, skills })
      setResult(data.text)
      decrementCredit('credits_resume')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка генерации')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(result)
    hapticMedium()
  }

  if (!user || user.credits_resume <= 0) {
    return (
      <div className="page">
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate('/')}>←</button>
          <h2>📄 Резюме</h2>
        </div>
        <p style={{ color: 'var(--tg-theme-hint-color)', marginBottom: 16 }}>У тебя закончились кредиты на резюме.</p>
        <button className="btn-primary" onClick={() => navigate('/payment')}>💳 Купить кредиты</button>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>📄 Резюме под вакансию</h2>
      </div>

      {!result ? (
        <>
          <div className="form-group">
            <label className="form-label">Текст вакансии *</label>
            <textarea className="text-input" rows={5} placeholder="Вставь описание вакансии с LinkedIn, Indeed..." value={vacancy} onChange={(e) => setVacancy(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Опыт работы *</label>
            <textarea className="text-input" rows={4} placeholder="Последние 3 места работы, достижения..." value={experience} onChange={(e) => setExperience(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Образование</label>
            <textarea className="text-input" rows={2} placeholder="ВУЗ, специальность, год..." value={education} onChange={(e) => setEducation(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Ключевые навыки *</label>
            <textarea className="text-input" rows={2} placeholder="Python, SQL, управление командой..." value={skills} onChange={(e) => setSkills(e.target.value)} />
          </div>
          {error && <p style={{ color: '#ff4d4f', marginBottom: 12, fontSize: 14 }}>{error}</p>}
          <button className="btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? '⏳ Создаю резюме...' : '✨ Создать резюме'}
          </button>
        </>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 8 }}>Резюме готово! Скопируй или начни заново.</p>
          <div className="result-box">{result}</div>
          <button className="btn-primary" style={{ marginBottom: 10 }} onClick={handleCopy}>📋 Скопировать</button>
          <button className="btn-secondary" onClick={() => { setResult(''); setVacancy('') }}>📄 Новое резюме</button>
        </>
      )}
    </div>
  )
}
