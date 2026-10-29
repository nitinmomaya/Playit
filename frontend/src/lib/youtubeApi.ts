// Make JSON requests through Axios.
import axios, { AxiosHeaders } from 'axios'
// Import youtubeAuth dependencies.
import { API_BASE_URL } from './apiConfig'
import { readYouTubeAuthState, type YouTubeProfile } from './youtubeAuth'

// Describe the YouTubeTokens data contract.
export type YouTubeTokens = {
  // Define access_token in this data shape.
  access_token: string
  // Define refresh_token in this data shape.
  refresh_token?: string
  // Define token_type in this data shape.
  token_type: string
  // Define expires_in in this data shape.
  expires_in: number
  // Define scope in this data shape.
  scope?: string
}

// Describe the YouTubeResource data contract.
export type YouTubeResource = {
  // Define id in this data shape.
  id: string
  // Define snippet in this data shape.
  snippet: { title: string; description?: string }
  // Define contentDetails in this data shape.
  contentDetails?: { itemCount?: number }
}
// Describe the YouTubePage data contract.
export type YouTubePage = {
  // Define items in this data shape.
  items: YouTubeResource[]
  // Define nextPageToken in this data shape.
  nextPageToken?: string
}

// Configure the backend base URL and JSON transport.
export const youtubeApi = axios.create({
  // Set the baseURL option/value.
  baseURL: `${API_BASE_URL}/youtube`,
  // Set the withCredentials option/value.
  withCredentials: true,
  // Set the headers option/value.
  headers: { 'Content-Type': 'application/json' },
})

// Call youtubeApi.interceptors.request.use.
youtubeApi.interceptors.request.use((config) => {
  // Prepare { access_token } for the following operation.
  const { access_token } = readYouTubeAuthState()
  config.headers = new AxiosHeaders(config.headers ?? {})
  // Refresh credentials belong in the request body, never the bearer header.
  if (access_token && config.url !== '/token') {
    // Call config.headers.set.
    config.headers.set('Authorization', `Bearer ${access_token}`)
  }
  // Return the current operation's result.
  return config
})

// Define the getYouTubeUser handler/helper.
export const getYouTubeUser = async () => {
  // Prepare response for the following operation.
  const response = await youtubeApi.get<YouTubeProfile>('/me')
  // Return the current operation's result.
  return response.data
}

// Define the refreshYouTubeToken handler/helper.
export const refreshYouTubeToken = async () => {
  // Prepare { refresh_token } for the following operation.
  const { refresh_token } = readYouTubeAuthState()
  // Check !refresh_token.
  if (!refresh_token) throw new Error('Reconnect YouTube to refresh your access.')
  // Prepare response for the following operation.
  const response = await youtubeApi.post<YouTubeTokens>('/token', {
    // Set the grant_type option/value.
    grant_type: 'refresh_token', refresh_token,
  })
  // Return the current operation's result.
  return response.data
}

// Define the getYouTubeChannels handler/helper.
export const getYouTubeChannels = async (signal?: AbortSignal) => {
  // Prepare response for the following operation.
  const response = await youtubeApi.get<YouTubePage>('/channels', { signal })
  // Return the current operation's result.
  return response.data
}

// Define the getYouTubePlaylists handler/helper.
export const getYouTubePlaylists = async (pageToken?: string, signal?: AbortSignal) => {
  // Prepare response for the following operation.
  const response = await youtubeApi.get<YouTubePage>('/playlists', {
    // Set the params option/value.
    params: { page_token: pageToken, max_results: 20 }, signal,
  })
  // Return the current operation's result.
  return response.data
}

// Describe the YouTubePlaylistMetadata data contract.
export type YouTubePlaylistMetadata = {
  // Define name in this data shape.
  name: string
  // Define description in this data shape.
  description?: string
  // Define privacy_status in this data shape.
  privacy_status?: 'private' | 'unlisted' | 'public'
}

// These helpers are explicit writes, not automatically executed by chat.
export const createYouTubePlaylist = async (metadata: YouTubePlaylistMetadata) => {
  // Prepare response for the following operation.
  const response = await youtubeApi.post<YouTubeResource>('/create_playlist', metadata)
  // Return the current operation's result.
  return response.data
}

// Define the updateYouTubePlaylist handler/helper.
export const updateYouTubePlaylist = async (playlistId: string, metadata: YouTubePlaylistMetadata) => {
  // Prepare response for the following operation.
  const response = await youtubeApi.put<YouTubeResource>(`/update_playlist/${encodeURIComponent(playlistId)}`, metadata)
  // Return the current operation's result.
  return response.data
}

// Define the deleteYouTubePlaylist handler/helper.
export const deleteYouTubePlaylist = async (playlistId: string) => {
  // Call youtubeApi.delete.
  await youtubeApi.delete(`/delete_playlist/${encodeURIComponent(playlistId)}`)
}

// Define the addYouTubePlaylistItem handler/helper.
export const addYouTubePlaylistItem = async (playlistId: string, videoId: string, position?: number) => {
  // Prepare response for the following operation.
  const response = await youtubeApi.post(`/add_item/${encodeURIComponent(playlistId)}/items`, {
    // Set the video_id option/value.
    video_id: videoId, position,
  })
  // Return the current operation's result.
  return response.data
}

// Define the removeYouTubePlaylistItem handler/helper.
export const removeYouTubePlaylistItem = async (playlistItemId: string) => {
  // Call youtubeApi.delete.
  await youtubeApi.delete(`/remove_item/${encodeURIComponent(playlistItemId)}/items`)
}

/* File summary
 * - Calls backend Google/YouTube endpoints with the selected account token.
 * - Exposes read, refresh, and explicit playlist/item write helpers.
 */
