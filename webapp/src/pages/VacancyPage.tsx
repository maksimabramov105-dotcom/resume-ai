import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeVacancy } from '../services/api'
import { hapticMedium } from '../services/telegram'

export default function VacancyPage() {
  const navigate = useNavigate()
  const [vacancy, setVacancy] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    if (!vacancy.trim()) { setError('Вставь текст вакансии'); return }
    setLoading(true); setError('')
    try {
      hapticMedium()
      const { data } = await analyzeVacancy({ vacancy_text: vacancy })
      setResult(data.text)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка анализа')
    } finally { setLoading(false) }
  }

  return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>🔍 Анализ вакансии</h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 14 }}>
        Бесплатный разбор: требования, ATS-слова, зарплата, красные флаги.
      </p>
      {!result ? (
        <>
          <div className="form-group">
            <label className="form-label">Текст вакансии</label>
            <textarea className="text-input" rows={8} placeholder="Вставь описание вакансии с hh.ru..." value={vacancy} onChange={(e) => setVacancy(e.target.value)} />
          </div>
          {error && <p style={{ color: '#ff4d4f', marginBottom: 12, fontSize: 14 }}>{error}</p>}
          <button className="btn-primary" onClick={handleAnalyze} disabled={loading}>
            {loading ? '🔍 Анализирую...' : '🔍 Анализировать'}
          </button>
        </>
      ) : (
        <>
          <div className="result-box">{result}</div>
          <button className="btn-primary" style={{ marginBottom: 10 }} onClick={() => navigate('/resume')}>📄 Создать резюме под эту вакансию</button>
          <button className="btn-secondary" onClick={() => { setResult(''); setVacancy('') }}>🔍 Новый анализ</button>
        </>
      )}
    </div>
  )
}
