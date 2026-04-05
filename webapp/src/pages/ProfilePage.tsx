import { useNavigate } from 'react-router-dom'
import { useUserStore } from '../stores/userStore'
import { getTelegramUser } from '../services/telegram'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user } = useUserStore()
  const tgUser = getTelegramUser()

  if (!user) return null

  const subLabels: Record<string, string> = {
    free: 'Бесплатный',
    basic: '📄 Базовый',
    pro: '⭐ Про',
    vip: '👑 VIP',
    assistant_unlimited: '💬 AI Безлимит',
  }

  const balance = [
    { icon: '📄', count: user.credits_resume,       label: 'Резюме' },
    { icon: '✉️', count: user.credits_cover_letter, label: 'Письма' },
    { icon: '🎯', count: user.credits_interview,    label: 'Собесы' },
    { icon: '💬', count: user.credits_assistant,    label: 'AI-чат' },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <h2>👤 Профиль</h2>
      </div>

      <div className="profile-section">
        <h3>Аккаунт</h3>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{user.full_name || tgUser?.first_name || '—'}</div>
            {user.username && <div style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)' }}>@{user.username}</div>}
          </div>
          <span className="tag success">{subLabels[user.subscription_type] ?? user.subscription_type}</span>
        </div>
      </div>

      <div className="profile-section">
        <h3>Баланс кредитов</h3>
        <div className="balance-grid">
          {balance.map((b) => (
            <div key={b.label} className="balance-item">
              <div className="bal-icon">{b.icon}</div>
              <div className="bal-count" style={{ color: b.count === 0 ? '#ff4d4f' : undefined }}>{b.count}</div>
              <div className="bal-label">{b.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="profile-section">
        <h3>Статистика</h3>
        {[
          ['Резюме создано', user.total_resumes_generated],
          ['AI-сообщений отправлено', user.total_assistant_messages],
          ['Потрачено', `${Math.round(user.total_spent_rub)} ₽`],
        ].map(([label, val]) => (
          <div key={String(label)} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 14 }}>
            <span style={{ color: 'var(--tg-theme-hint-color)' }}>{label}</span>
            <span style={{ fontWeight: 600 }}>{val}</span>
          </div>
        ))}
      </div>

      <button className="btn-primary" onClick={() => navigate('/payment')}>💳 Пополнить баланс</button>
    </div>
  )
}
