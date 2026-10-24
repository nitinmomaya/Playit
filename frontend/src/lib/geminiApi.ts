import axios from 'axios'
import { API_BASE_URL } from './apiConfig'


export const geminiApi = axios.create({
  baseURL: `${API_BASE_URL}/gemini`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})


export const createGeminiInteraction = async (data: { prompt: string; signal?: AbortSignal }) => {
  if (!data.prompt || typeof data.prompt !== 'string') {
    throw new Error('A valid prompt is required')
  }
  const response = await geminiApi.post<{ output: string }>(
    '/interactions', { prompt: data.prompt }, { signal: data.signal },
  )
  return response.data
}