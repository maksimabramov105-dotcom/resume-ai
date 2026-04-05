import { NavLink } from 'react-router-dom'

const items = [
  { to: '/',          icon: '🏠', label: 'Главная' },
  { to: '/vacancy',   icon: '🔍', label: 'Вакансия' },
  { to: '/assistant', icon: '💬', label: 'AI' },
  { to: '/profile',   icon: '👤', label: 'Профиль' },
  { to: '/payment',   icon: '💳', label: 'Купить' },
]

export default function BottomNav() {
  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) => isActive ? 'active' : ''}
        >
          <span className="nav-icon">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
