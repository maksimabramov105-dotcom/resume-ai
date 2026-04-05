import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateCoverLetter } from '../services/api'
import { useUserStore } from '../stores/userStore'
import { hapticMedium } from '../services/telegram'

export default function CoverLetterPage() {
  const navigate = useNavigate()
  const { user, decrementCredit } = useUserStore()
  const [vacancy, setVacancy] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!vacancy.trim()) { setError('Вставь текст вакансии'); return }
    setLoading(true); setError('')
    try {
      hapticMedium()
      const { data } = await generateCoverLetter({ vacancy_text: vacancy })
      setResult(data.text)
      decrementCredit('credits_cover_letter')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка генерации')
    } finally { setLoading(false) }
  }

  if (!user || user.credits_cover_letter <= 0) {
    return (
      <div className="page">
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate('/')}>←</button>
          <h2>✉️ Письмо</h2>
        </div>
        <p style={{ color: 'var(--tg-theme-hint-color)', marginBottom: 16 }}>Кредиты на письма закончились.</p>
        <button className="btn-primary" onClick={() => navigate('/payment')}>💳 Купить кредиты</button>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>✉️ Сопроводительное письмо</h2>
      </div>
      {!result ? (
        <>
          <div className="form-group">
            <label className="form-label">Текст вакансии *</label>
            <textarea className="text-input" rows={6} placeholder="Вставь описание вакансии..." value={vacancy} onChange={(e) => setVacancy(e.target.value)} />
          </div>
          {error && <p style={{ color: '#ff4d4f', marginBottom: 12, fontSize: 14 }}>{error}</p>}
          <button className="btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? '⏳ Пишу письмо...' : '✨ Написать письмо'}
          </button>
        </>
      ) : (
        <>
          <div className="result-box">{result}</div>
          <button className="btn-primary" style={{ marginBottom: 10 }} onClick={() => { navigator.clipboard.writeText(result); hapticMedium() }}>📋 Скопировать</button>
          <button className="btn-secondary" onClick={() => { setResult(''); setVacancy('') }}>✉️ Новое письмо</button>
        </>
      )}
    </div>
  )
}
