// Make JSON requests through Axios.
import axios from 'axios'
import { API_BASE_URL } from './apiConfig'


// Configure the backend base URL and JSON transport.
export const geminiApi = axios.create({
  // Set the baseURL option/value.
  baseURL: `${API_BASE_URL}/gemini`,
  // Set the withCredentials option/value.
  withCredentials: true,
  // Set the headers option/value.
  headers: {
    // Set the 'Content-Type' option/value.
    'Content-Type': 'application/json',
  },
})


// Define the createGeminiInteraction handler/helper.
export const createGeminiInteraction = async (data: { prompt: string; signal?: AbortSignal }) => {
  // Check !data.prompt || typeof data.prompt !== 'string'.
  if (!data.prompt || typeof data.prompt !== 'string') {
    // Reject invalid input or a failed operation.
    throw new Error('A valid prompt is required')
  }
  // Prepare response for the following operation.
  const response = await geminiApi.post<{ output: string }>(
    '/interactions', { prompt: data.prompt }, { signal: data.signal },
  )
  // Return the current operation's result.
  return response.data
}

/* File summary
 * - Configures the backend Gemini JSON client.
 * - Provides a completed-response interaction helper.
 */
