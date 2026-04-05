import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createPayment, checkCryptoPayment } from '../services/api'
import { hapticMedium, openLink } from '../services/telegram'
import { useUserStore } from '../stores/userStore'

const PACKAGES = [
  { key: 'basic',              name: '📄 Базовый',           price: '299₽',  usdt: '3.30',  desc: '3 резюме + 3 письма + 1 собес + 10 AI' },
  { key: 'pro',                name: '⭐ Про',                price: '790₽',  usdt: '8.80',  desc: '10 резюме + 10 писем + 5 собесов + 50 AI' },
  { key: 'vip',                name: '👑 VIP 30 дней',        price: '1990₽', usdt: '22.00', desc: 'Безлимит на всё' },
  { key: 'assistant_50',       name: '💬 50 сообщений AI',    price: '149₽',  usdt: '1.65',  desc: 'Только AI-ассистент' },
  { key: 'assistant_200',      name: '💬 200 сообщений AI',   price: '399₽',  usdt: '4.40',  desc: 'Только AI-ассистент' },
  { key: 'assistant_unlimited',name: '💬 AI Безлимит 30 дней',price: '690₽',  usdt: '7.65',  desc: 'Безлим AI-ассистент' },
]

const METHODS = [
  { key: 'crypto',  icon: '💎', title: 'Криптовалюта (USDT)', desc: 'Автоматически через @CryptoBot' },
  { key: 'rucard',  icon: '🇷🇺', title: 'Карта РФ',            desc: 'Перевод на карту (ручное подтверждение)' },
  { key: 'revolut', icon: '💳', title: 'Revolut',              desc: 'Перевод на Revolut (ручное подтверждение)' },
]

type PaymentData = {
  method: string
  payment_url?: string
  invoice_id?: string
  card_number?: string
  card_holder?: string
  bank_name?: string
  revolut_tag?: string
  revolut_link?: string
  amount_rub?: number
  amount_usdt?: number
  payment_db_id?: number
}

export default function PaymentPage() {
  const navigate = useNavigate()
  const { fetchUser } = useUserStore()
  const [selectedPkg, setSelectedPkg] = useState('')
  const [selectedMethod, setSelectedMethod] = useState('')
  const [loading, setLoading] = useState(false)
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null)
  const [checkLoading, setCheckLoading] = useState(false)
  const [checkResult, setCheckResult] = useState('')
  const [error, setError] = useState('')

  const handlePay = async () => {
    if (!selectedPkg || !selectedMethod) { setError('Выбери пакет и способ оплаты'); return }
    setLoading(true); setError('')
    hapticMedium()
    try {
      const { data } = await createPayment({ package: selectedPkg, method: selectedMethod })
      setPaymentData(data)

      if (data.method === 'crypto' && data.payment_url) {
        openLink(data.payment_url)
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка создания платежа')
    } finally { setLoading(false) }
  }

  const handleCheckCrypto = async () => {
    if (!paymentData?.invoice_id) return
    setCheckLoading(true); setCheckResult('')
    try {
      const { data } = await checkCryptoPayment(paymentData.invoice_id, selectedPkg)
      if (data.status === 'paid') {
        setCheckResult('✅ Оплата подтверждена! Баланс обновлён.')
        await fetchUser()
      } else if (data.status === 'expired') {
        setCheckResult('❌ Инвойс истёк. Создай новый.')
        setPaymentData(null)
      } else {
        setCheckResult('⏳ Платёж ещё не поступил. Попробуй через минуту.')
      }
    } finally { setCheckLoading(false) }
  }

  const pkg = PACKAGES.find((p) => p.key === selectedPkg)

  // --- Show payment instructions ---
  if (paymentData) {
    return (
      <div className="page">
        <div className="page-header">
          <button className="back-btn" onClick={() => setPaymentData(null)}>←</button>
          <h2>💳 Оплата</h2>
        </div>

        {paymentData.method === 'crypto' && (
          <>
            <div className="payment-details">
              <h4>💎 Оплата криптовалютой (USDT)</h4>
              <div className="detail-row"><span className="label">Сумма</span><span className="value">{paymentData.amount_usdt} USDT</span></div>
              <div className="detail-row"><span className="label">≈ в рублях</span><span className="value">{paymentData.amount_rub} ₽</span></div>
            </div>
            <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 14 }}>
              Ссылка на оплату открылась в браузере. После оплаты нажми «Проверить».
            </p>
            <button className="btn-primary" style={{ marginBottom: 10 }} onClick={() => paymentData.payment_url && openLink(paymentData.payment_url)}>
              🔗 Открыть ссылку снова
            </button>
            <button className="btn-secondary" onClick={handleCheckCrypto} disabled={checkLoading}>
              {checkLoading ? '⏳ Проверяю...' : '✅ Проверить оплату'}
            </button>
            {checkResult && <p style={{ marginTop: 12, fontSize: 14, textAlign: 'center' }}>{checkResult}</p>}
          </>
        )}

        {paymentData.method === 'rucard' && (
          <>
            <div className="payment-details">
              <h4>🇷🇺 Перевод на карту РФ</h4>
              <div className="detail-row"><span className="label">Банк</span><span className="value">{paymentData.bank_name}</span></div>
              <div className="detail-row"><span className="label">Получатель</span><span className="value">{paymentData.card_holder}</span></div>
              <div className="detail-row"><span className="label">Номер карты</span><span className="value">{paymentData.card_number}</span></div>
              <div className="detail-row"><span className="label">Сумма</span><span className="value" style={{ color: 'var(--tg-theme-button-color)' }}>{paymentData.amount_rub} ₽</span></div>
              <p className="copy-hint">Нажми на номер карты чтобы скопировать</p>
            </div>
            <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 14, lineHeight: 1.5 }}>
              После перевода сделай скриншот и отправь его в бот @topbestworkerbot. Кредиты зачислятся после проверки (обычно до 15 мин).
            </p>
            <button className="btn-primary" onClick={() => navigate('/')}>🏠 На главную</button>
          </>
        )}

        {paymentData.method === 'revolut' && (
          <>
            <div className="payment-details">
              <h4>💳 Перевод на Revolut</h4>
              <div className="detail-row"><span className="label">Revolut</span><span className="value">{paymentData.revolut_tag}</span></div>
              <div className="detail-row"><span className="label">Сумма (RUB)</span><span className="value">{paymentData.amount_rub} ₽</span></div>
              <div className="detail-row"><span className="label">Сумма (USDT)</span><span className="value">{paymentData.amount_usdt} USDT</span></div>
            </div>
            {paymentData.revolut_link && (
              <button className="btn-primary" style={{ marginBottom: 10 }} onClick={() => openLink(paymentData.revolut_link!)}>
                💳 Открыть Revolut
              </button>
            )}
            <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 14, lineHeight: 1.5 }}>
              После перевода сделай скриншот и отправь его в бот @topbestworkerbot. Кредиты зачислятся после проверки.
            </p>
            <button className="btn-secondary" onClick={() => navigate('/')}>🏠 На главную</button>
          </>
        )}
      </div>
    )
  }

  // --- Package & method selection ---
  return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>💳 Купить кредиты</h2>
      </div>

      <p className="section-title">Выбери пакет</p>
      {PACKAGES.map((p) => (
        <div key={p.key} className={`package-card${selectedPkg === p.key ? ' selected' : ''}`} onClick={() => setSelectedPkg(p.key)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3>{p.name}</h3>
            <div>
              <span className="price">{p.price}</span>
              <span style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)', marginLeft: 6 }}>/ {p.usdt} USDT</span>
            </div>
          </div>
          <p className="desc">{p.desc}</p>
        </div>
      ))}

      <p className="section-title">Способ оплаты</p>
      {METHODS.map((m) => (
        <div key={m.key} className={`method-card${selectedMethod === m.key ? ' selected' : ''}`} onClick={() => setSelectedMethod(m.key)}>
          <span className="method-icon">{m.icon}</span>
          <div className="method-info">
            <h4>{m.title}</h4>
            <p>{m.desc}</p>
          </div>
        </div>
      ))}

      {error && <p style={{ color: '#ff4d4f', fontSize: 14, marginBottom: 12 }}>{error}</p>}

      <button className="btn-primary" onClick={handlePay} disabled={loading || !selectedPkg || !selectedMethod}>
        {loading ? '⏳ Создаю...' : `Оплатить${pkg ? ` — ${pkg.price}` : ''}`}
      </button>
    </div>
  )
}
