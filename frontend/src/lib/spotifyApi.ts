// Make JSON requests through Axios.
import axios, { AxiosHeaders, type RawAxiosRequestHeaders } from 'axios'

// Import auth dependencies.
import { readSpotifyAuthState, type SpotifyProfile } from './auth'

// Describe the SpotifyTokens data contract.
export type SpotifyTokens = {
  // Define access_token in this data shape.
  access_token: string
  // Define refresh_token in this data shape.
  refresh_token: string
  // Define token_type in this data shape.
  token_type: string
  // Define expires_in in this data shape.
  expires_in: number
  // Define scope in this data shape.
  scope?: string
}

// Describe the SpotifyPlaylist data contract.
export type SpotifyPlaylist = {
  // Define id in this data shape.
  id: string
  // Define name in this data shape.
  name: string
  [key: string]: unknown
}

// Describe the SpotifyPlaylists data contract.
export type SpotifyPlaylists = {
  // Define items in this data shape.
  items: SpotifyPlaylist[]
  // Define total in this data shape.
  total: number
}

// Configure the backend base URL and JSON transport.
export const spotifyApi = axios.create({
  // Set the baseURL option/value.
  baseURL: 'http://127.0.0.1:8000/spotify',
  // Set the withCredentials option/value.
  withCredentials: true,
  // Set the headers option/value.
  headers: {
    // Set the 'Content-Type' option/value.
    'Content-Type': 'application/json',
  },
})

// Define the getSpotifyAuthHeaders handler/helper.
export const getSpotifyAuthHeaders = (): RawAxiosRequestHeaders => {
  // Prepare { access_token } for the following operation.
  const { access_token } = readSpotifyAuthState()

  // Return the current operation's result.
  return {
    ...(access_token ? { Authorization: `Bearer ${access_token}` } : {}),
  }
}

// Call spotifyApi.interceptors.request.use.
spotifyApi.interceptors.request.use((config) => {
  // Prepare { access_token } for the following operation.
  const { access_token } = readSpotifyAuthState()

  config.headers = new AxiosHeaders(config.headers ?? {})

  // Check access_token.
  if (access_token) {
    // Call config.headers.set.
    config.headers.set('Authorization', `Bearer ${access_token}`)
  }

  // Return the current operation's result.
  return config
})

// Define the getSpotifyUser handler/helper.
export const getSpotifyUser = async () => {
  // Prepare { access_token } for the following operation.
  const { access_token } = readSpotifyAuthState()

  // Check !access_token.
  if (!access_token) {
    // Reject invalid input or a failed operation.
    throw new Error('No Spotify access token available')
  }

  // Prepare response for the following operation.
  const response = await spotifyApi.get<SpotifyProfile>('/me', {
    // Set the headers option/value.
    headers: getSpotifyAuthHeaders(),
  })

  // Return the current operation's result.
  return response.data
}

// Define the getSpotifyTokens handler/helper.
export const getSpotifyTokens = async (code: string, state: string) => {
  // Prepare response for the following operation.
  const response = await spotifyApi.post<SpotifyTokens>('/token', {
    // Set the grant_type option/value.
    grant_type: 'authorization_code',
    code,
    state,
  })
  // Return the current operation's result.
  return response.data
}

// Define the refreshSpotifyToken handler/helper.
export const refreshSpotifyToken = async () => {
  // Prepare { refresh_token } for the following operation.
  const { refresh_token } = readSpotifyAuthState()

  // Check !refresh_token.
  if (!refresh_token) {
    // Reject invalid input or a failed operation.
    throw new Error('No Spotify refresh token available')
  }

  // Prepare response for the following operation.
  const response = await spotifyApi.post<SpotifyTokens>('/token', {
    // Set the grant_type option/value.
    grant_type: 'refresh_token',
    refresh_token,
  })

  // Return the current operation's result.
  return response.data
}

// Define the getSpotifyUserPlaylists handler/helper.
export const getSpotifyUserPlaylists = async (userId: string) => {
  // Check !readSpotifyAuthState().access_token.
  if (!readSpotifyAuthState().access_token) {
    // Reject invalid input or a failed operation.
    throw new Error('No Spotify access token available')
  }
  // Check !userId.trim().
  if (!userId.trim()) {
    // Reject invalid input or a failed operation.
    throw new Error('A Spotify user ID is required')
  }
  // Prepare response for the following operation.
  const response = await spotifyApi.get<SpotifyPlaylists>(
    `/users/${encodeURIComponent(userId)}/playlists`,
  )
  // Return the current operation's result.
  return response.data
}

/* File summary
 * - Calls backend Spotify endpoints through an Axios client.
 * - Adds the current access token and exposes profile/playlist/token helpers.
 */
