import axios, { AxiosHeaders } from 'axios'
import { readYouTubeAuthState, type YouTubeProfile } from './youtubeAuth'

export type YouTubeTokens = {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in: number
  scope?: string
}

export type YouTubeResource = {
  id: string
  snippet: { title: string; description?: string }
  contentDetails?: { itemCount?: number }
}
export type YouTubePage = {
  items: YouTubeResource[]
  nextPageToken?: string
}

export const youtubeApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/youtube',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

youtubeApi.interceptors.request.use((config) => {
  const { access_token } = readYouTubeAuthState()
  config.headers = new AxiosHeaders(config.headers ?? {})
  // Refresh credentials belong in the request body, never the bearer header.
  if (access_token && config.url !== '/token') {
    config.headers.set('Authorization', `Bearer ${access_token}`)
  }
  return config
})

export const getYouTubeUser = async () => {
  const response = await youtubeApi.get<YouTubeProfile>('/me')
  return response.data
}

export const refreshYouTubeToken = async () => {
  const { refresh_token } = readYouTubeAuthState()
  if (!refresh_token) throw new Error('Reconnect YouTube to refresh your access.')
  const response = await youtubeApi.post<YouTubeTokens>('/token', {
    grant_type: 'refresh_token', refresh_token,
  })
  return response.data
}

export const getYouTubeChannels = async (signal?: AbortSignal) => {
  const response = await youtubeApi.get<YouTubePage>('/channels', { signal })
  return response.data
}

export const getYouTubePlaylists = async (pageToken?: string, signal?: AbortSignal) => {
  const response = await youtubeApi.get<YouTubePage>('/playlists', {
    params: { page_token: pageToken, max_results: 20 }, signal,
  })
  return response.data
}

export type YouTubePlaylistMetadata = {
  name: string
  description?: string
  privacy_status?: 'private' | 'unlisted' | 'public'
}

// These helpers are explicit writes, not automatically executed by chat.
export const createYouTubePlaylist = async (metadata: YouTubePlaylistMetadata) => {
  const response = await youtubeApi.post<YouTubeResource>('/create_playlist', metadata)
  return response.data
}

export const updateYouTubePlaylist = async (playlistId: string, metadata: YouTubePlaylistMetadata) => {
  const response = await youtubeApi.put<YouTubeResource>(`/update_playlist/${encodeURIComponent(playlistId)}`, metadata)
  return response.data
}

export const deleteYouTubePlaylist = async (playlistId: string) => {
  await youtubeApi.delete(`/delete_playlist/${encodeURIComponent(playlistId)}`)
}

export const addYouTubePlaylistItem = async (playlistId: string, videoId: string, position?: number) => {
  const response = await youtubeApi.post(`/add_item/${encodeURIComponent(playlistId)}/items`, {
    video_id: videoId, position,
  })
  return response.data
}

export const removeYouTubePlaylistItem = async (playlistItemId: string) => {
  await youtubeApi.delete(`/remove_item/${encodeURIComponent(playlistItemId)}/items`)
}