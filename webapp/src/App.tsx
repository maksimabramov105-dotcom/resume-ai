import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useUserStore } from './stores/userStore'

import HomePage from './pages/HomePage'
import ResumePage from './pages/ResumePage'
import CoverLetterPage from './pages/CoverLetterPage'
import InterviewPage from './pages/InterviewPage'
import VacancyPage from './pages/VacancyPage'
import AssistantPage from './pages/AssistantPage'
import ProfilePage from './pages/ProfilePage'
import PaymentPage from './pages/PaymentPage'
import BottomNav from './components/BottomNav'
import LoadingSpinner from './components/LoadingSpinner'

export default function App() {
  const { fetchUser, loading } = useUserStore()

  useEffect(() => {
    fetchUser()
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <BrowserRouter>
      <div className="app-container">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/resume" element={<ResumePage />} />
          <Route path="/cover-letter" element={<CoverLetterPage />} />
          <Route path="/interview" element={<InterviewPage />} />
          <Route path="/vacancy" element={<VacancyPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/payment" element={<PaymentPage />} />
        </Routes>
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
