import axios from 'axios'
import { spotifyApi } from './spotifyApi'
import type { ConversationTurn } from './chatApi'

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
  proposal: { name: string; description: string; public: boolean }
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

export async function preparePlaylist(prompt: string, signal: AbortSignal, history: ConversationTurn[] = []) {
  const { data } = await spotifyApi.post<{
    message: string
    name: string
    description: string
    requested_count: number | null
    target_duration_ms: number | null
    recommendations: { songname: string; artistname: string }[]
  }>('/recommendations', { prompt, history }, { signal })
  signal.throwIfAborted()
  const response = await spotifyApi.post<PlaylistPreview>('/music/drafts', {
    name: data.name, description: data.description, public: false, songs: data.recommendations,
    requested_count: data.requested_count, target_duration_ms: data.target_duration_ms,
  }, { ...config, signal })
  return {
    preview: response.data,
    // Retain the model's original suggestions separately from Spotify matches.
    // Only this independently generated text may enter future Gemini context.
    contextText: JSON.stringify({ message: data.message, name: data.name,
      description: data.description, recommendations: data.recommendations }),
  }
}

export async function approveAndCreatePlaylist(draftId: string) {
  await spotifyApi.post(`${path(draftId)}/approve`, null, config)
  const { data } = await spotifyApi.post<PlaylistResult>(`${path(draftId)}/create`, null, config)
  return data
}

export async function getPlaylistPreview(draftId: string) {
  const { data } = await spotifyApi.get<PlaylistPreview>(path(draftId), config)
  return data
}

export function musicErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail : 'Request failed. Check your connection and Spotify login.'
  }
  return error instanceof Error ? error.message : 'Could not build the playlist.'
}