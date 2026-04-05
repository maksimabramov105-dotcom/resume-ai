export default function LoadingSpinner() {
  return (
    <div className="loading-screen">
      <div className="spinner" />
      <p style={{ color: 'var(--tg-theme-hint-color)', fontSize: 14 }}>Загрузка...</p>
    </div>
  )
}
