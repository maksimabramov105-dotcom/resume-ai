import { useNavigate } from 'react-router-dom'
import { useUserStore } from '../stores/userStore'
import { getTelegramUser } from '../services/telegram'
import CreditBadge from '../components/CreditBadge'

export default function HomePage() {
  const navigate = useNavigate()
  const { user } = useUserStore()
  const tgUser = getTelegramUser()

  const features = [
    { icon: '📄', title: 'Резюме под вакансию', desc: 'AI создаст идеальное резюме + PDF', path: '/resume', credits: user?.credits_resume },
    { icon: '✉️', title: 'Сопроводительное письмо', desc: 'Персональное письмо за 30 сек', path: '/cover-letter', credits: user?.credits_cover_letter },
    { icon: '🎯', title: 'Симуляция собеседования', desc: 'Потренируйся с AI-HR', path: '/interview', credits: user?.credits_interview },
    { icon: '🔍', title: 'Анализ вакансии', desc: 'Разбор требований — бесплатно', path: '/vacancy', credits: '∞' },
    { icon: '💬', title: 'AI-ассистент', desc: 'Задай любой вопрос', path: '/assistant', credits: user?.credits_assistant },
  ]

  return (
    <div className="page">
      <div className="hero">
        <h1>👋 Привет{tgUser?.first_name ? `, ${tgUser.first_name}` : ''}!</h1>
        <p>Что хочешь сделать сегодня?</p>
      </div>

      <div className="features-grid">
        {features.map((f) => (
          <button
            key={f.path}
            className={`feature-card${f.credits === 0 ? ' disabled' : ''}`}
            onClick={() => navigate(f.path)}
          >
            <span className="feature-icon">{f.icon}</span>
            <div className="feature-info">
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
            <CreditBadge count={f.credits} />
          </button>
        ))}
      </div>

      <button className="btn-primary" onClick={() => navigate('/payment')}>
        💳 Купить кредиты
      </button>
    </div>
  )
}
