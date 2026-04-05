import axios from 'axios'
import { getInitData } from './telegram'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  config.headers['X-Telegram-Init-Data'] = getInitData()
  return config
})

// User
export const getUser = () => api.get('/user/me')

// Resume
export const generateResume = (data: {
  vacancy_text: string
  experience: string
  education: string
  skills: string
}) => api.post('/resume/generate', data)

// Cover Letter
export const generateCoverLetter = (data: {
  vacancy_text: string
  candidate_summary?: string
}) => api.post('/cover-letter/generate', data)

// Interview
export const startInterview = (data: {
  vacancy_text: string
  candidate_summary?: string
}) => api.post('/interview/start', data)

export const answerInterview = (data: {
  answer: string
  vacancy_text: string
  candidate_summary?: string
  conversation_history: Array<{ role: string; content: string }>
}) => api.post('/interview/answer', data)

export const finishInterview = (data: {
  answer: string
  vacancy_text: string
  candidate_summary?: string
  conversation_history: Array<{ role: string; content: string }>
}) => api.post('/interview/finish', data)

// Vacancy
export const analyzeVacancy = (data: { vacancy_text: string }) =>
  api.post('/vacancy/analyze', data)

// Assistant
export const sendAssistantMessage = (data: { message: string }) =>
  api.post('/assistant/message', data)

export const clearAssistantHistory = () => api.delete('/assistant/history')

// Payment
export const createPayment = (data: { package: string; method: string }) =>
  api.post('/payment/create', data)

export const checkCryptoPayment = (invoiceId: string, pkg: string) =>
  api.get(`/payment/check/${invoiceId}?package=${pkg}`)

export default api
