import axios from 'axios'
import { spotifyApi } from './spotifyApi'
import { youtubeApi } from './youtubeApi'
import type { ConversationTurn } from './chatApi'

export type MusicProvider = 'spotify' | 'youtube'
const clientFor = (provider: MusicProvider) => provider === 'youtube' ? youtubeApi : spotifyApi

export type PlaylistResult = {
  url: string
  status: 'complete' | 'partial' | 'needs_review'
  added: number
  total: number
}

export type PlaylistPreview = {
  draft_id: string
  matched_count: number
  total_duration_ms: number
  constraint_warning: string | null
  proposal: { provider: MusicProvider; name: string; description: string; public: boolean }
  matches: {
    recommendation: { title: string; artist: string }
    status: 'matched' | 'not_found' | 'ambiguous' | 'duplicate' | 'not_selected'
    track: { title: string; artists: string[] } | null
  }[]
  result: PlaylistResult | null
}

// Keep the existing Spotify bearer interceptor. Transport credentials never go
// into Gemini prompts; catalog results are rendered locally, not sent to Gemini.
const config = { baseURL: new URL('..', `${spotifyApi.defaults.baseURL}/`).href }
const path = (draftId: string) => `/music/drafts/${encodeURIComponent(draftId)}`

export async function preparePlaylist(prompt: string, signal: AbortSignal, history: ConversationTurn[] = [], provider: MusicProvider = 'spotify') {
  const { data } = await clientFor(provider).post<{ preview: PlaylistPreview; context_text: string }>(
    '/music/recommendations', { prompt, history }, { ...config, signal, params: { provider } },
  )
  return { preview: data.preview, contextText: data.context_text }
}

export async function runPlaylistAgent(prompt: string, signal: AbortSignal, history: ConversationTurn[] = [], provider: MusicProvider = 'spotify') {
  const agentBaseUrl = new URL('gemini/', config.baseURL).href
  const { data } = await clientFor(provider).post<{ text: string; draft_id: string | null; context_text: string | null }>(
    'agent', { prompt, history }, { baseURL: agentBaseUrl, signal, params: { provider } },
  )
  const preview = data.draft_id ? await getPlaylistPreview(data.draft_id, provider) : null
  return { text: data.text, contextText: data.context_text, preview }
}

export async function approveAndCreatePlaylist(draftId: string, provider: MusicProvider = 'spotify') {
  const api = clientFor(provider)
  await api.post(`${path(draftId)}/approve`, null, config)
  const { data } = await api.post<PlaylistResult>(`${path(draftId)}/create`, null, config)
  return data
}

export async function getPlaylistPreview(draftId: string, provider: MusicProvider = 'spotify') {
  const { data } = await clientFor(provider).get<PlaylistPreview>(path(draftId), config)
  return data
}

export function musicErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail : 'Request failed. Check your connection and music account login.'
  }
  return error instanceof Error ? error.message : 'Could not build the playlist.'
}