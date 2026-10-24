// Make JSON requests through Axios.
import axios from 'axios'
// Import spotifyApi dependencies.
import { spotifyApi } from './spotifyApi'
// Import youtubeApi dependencies.
import { youtubeApi } from './youtubeApi'
// Import chatApi dependencies.
import type { ConversationTurn } from './chatApi'

// Describe the MusicProvider data contract.
export type MusicProvider = 'spotify' | 'youtube'
// Define the clientFor handler/helper.
const clientFor = (provider: MusicProvider) => provider === 'youtube' ? youtubeApi : spotifyApi

// Describe the PlaylistResult data contract.
export type PlaylistResult = {
  // Define url in this data shape.
  url: string
  // Define status in this data shape.
  status: 'complete' | 'partial' | 'needs_review'
  // Define added in this data shape.
  added: number
  // Define total in this data shape.
  total: number
}

// Describe the PlaylistPreview data contract.
export type PlaylistPreview = {
  // Define draft_id in this data shape.
  draft_id: string
  // Define matched_count in this data shape.
  matched_count: number
  // Define total_duration_ms in this data shape.
  total_duration_ms: number
  // Define constraint_warning in this data shape.
  constraint_warning: string | null
  // Define proposal in this data shape.
  proposal: { provider: MusicProvider; name: string; description: string; public: boolean }
  // Define matches in this data shape.
  matches: {
    // Define recommendation in this data shape.
    recommendation: { title: string; artist: string }
    // Define status in this data shape.
    status: 'matched' | 'not_found' | 'ambiguous' | 'duplicate' | 'not_selected'
    // Define track in this data shape.
    track: { title: string; artists: string[] } | null
  }[]
  // Define result in this data shape.
  result: PlaylistResult | null
}

// Keep the existing Spotify bearer interceptor. Transport credentials never go
// into Gemini prompts; catalog results are rendered locally, not sent to Gemini.
const config = { baseURL: new URL('..', `${spotifyApi.defaults.baseURL}/`).href }
// Define the path handler/helper.
const path = (draftId: string) => `/music/drafts/${encodeURIComponent(draftId)}`

// Define preparePlaylist as an async operation.
export async function preparePlaylist(prompt: string, signal: AbortSignal, history: ConversationTurn[] = [], provider: MusicProvider = 'spotify') {
  // Prepare { data } for the following operation.
  const { data } = await clientFor(provider).post<{ preview: PlaylistPreview; context_text: string }>(
    '/music/recommendations', { prompt, history }, { ...config, signal, params: { provider } },
  )
  // Return the current operation's result.
  return { preview: data.preview, contextText: data.context_text }
}

// Define runPlaylistAgent as an async operation.
export async function runPlaylistAgent(prompt: string, signal: AbortSignal, history: ConversationTurn[] = [], provider: MusicProvider = 'spotify') {
  // Prepare agentBaseUrl for the following operation.
  const agentBaseUrl = new URL('gemini/', config.baseURL).href
  // Prepare { data } for the following operation.
  const { data } = await clientFor(provider).post<{ text: string; draft_id: string | null; context_text: string | null }>(
    'agent', { prompt, history }, { baseURL: agentBaseUrl, signal, params: { provider } },
  )
  // Prepare preview for the following operation.
  const preview = data.draft_id ? await getPlaylistPreview(data.draft_id, provider) : null
  // Return the current operation's result.
  return { text: data.text, contextText: data.context_text, preview }
}

// Define approveAndCreatePlaylist as an async operation.
export async function approveAndCreatePlaylist(draftId: string, provider: MusicProvider = 'spotify') {
  // Prepare api for the following operation.
  const api = clientFor(provider)
  // Call api.post.
  await api.post(`${path(draftId)}/approve`, null, config)
  // Prepare { data } for the following operation.
  const { data } = await api.post<PlaylistResult>(`${path(draftId)}/create`, null, config)
  // Return the current operation's result.
  return data
}

// Define getPlaylistPreview as an async operation.
export async function getPlaylistPreview(draftId: string, provider: MusicProvider = 'spotify') {
  // Prepare { data } for the following operation.
  const { data } = await clientFor(provider).get<PlaylistPreview>(path(draftId), config)
  // Return the current operation's result.
  return data
}

// Define musicErrorMessage.
export function musicErrorMessage(error: unknown) {
  // Check axios.isAxiosError(error).
  if (axios.isAxiosError(error)) {
    // Return the current operation's result.
    return typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail : 'Request failed. Check your connection and music account login.'
  }
  // Return the current operation's result.
  return error instanceof Error ? error.message : 'Could not build the playlist.'
}

/* File summary
 * - Selects the correct provider bearer client for shared music routes.
 * - Fetches graph/agent previews and submits approval before creation.
 * - Converts backend failures into readable UI errors.
 */
