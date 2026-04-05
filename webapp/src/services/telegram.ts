import WebApp from '@twa-dev/sdk'

export function initTelegram() {
  WebApp.ready()
  WebApp.expand()
  WebApp.enableClosingConfirmation()
}

export function getTelegramUser() {
  return WebApp.initDataUnsafe?.user
}

export function getInitData(): string {
  return WebApp.initData
}

export function getThemeParams() {
  return WebApp.themeParams
}

export function closeMiniApp() {
  WebApp.close()
}

export function showAlert(message: string) {
  WebApp.showAlert(message)
}

export function hapticLight() {
  WebApp.HapticFeedback.impactOccurred('light')
}

export function hapticMedium() {
  WebApp.HapticFeedback.impactOccurred('medium')
}

export function openLink(url: string) {
  WebApp.openLink(url)
}
