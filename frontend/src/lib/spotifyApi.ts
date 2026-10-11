import axios, { AxiosHeaders, type RawAxiosRequestHeaders } from 'axios'

import { readSpotifyAuthState, type SpotifyProfile } from './auth'

export type SpotifyTokens = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  scope?: string
}

export type SpotifyPlaylist = {
  id: string
  name: string
  [key: string]: unknown
}

export type SpotifyPlaylists = {
  items: SpotifyPlaylist[]
  total: number
}

export const spotifyApi = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getSpotifyAuthHeaders = (): RawAxiosRequestHeaders => {
  const { access_token } = readSpotifyAuthState()

  return {
    ...(access_token ? { Authorization: `Bearer ${access_token}` } : {}),
  }
}

spotifyApi.interceptors.request.use((config) => {
  const { access_token } = readSpotifyAuthState()

  config.headers = new AxiosHeaders(config.headers ?? {})

  if (access_token) {
    config.headers.set('Authorization', `Bearer ${access_token}`)
  }

  return config
})

export const getSpotifyUser = async () => {
  const { access_token } = readSpotifyAuthState()

  if (!access_token) {
    throw new Error('No Spotify access token available')
  }

  const response = await spotifyApi.get<SpotifyProfile>('/spotify/me', {
    headers: getSpotifyAuthHeaders(),
  })

  return response.data
}

export const getSpotifyTokens = async (code: string, state: string) => {
  const response = await spotifyApi.post<SpotifyTokens>('/spotify/token', {
    grant_type: 'authorization_code',
    code,
    state,
  })
  return response.data
}

export const refreshSpotifyToken = async () => {
  const { refresh_token } = readSpotifyAuthState()

  if (!refresh_token) {
    throw new Error('No Spotify refresh token available')
  }

  const response = await spotifyApi.post<SpotifyTokens>('/spotify/token', {
    grant_type: 'refresh_token',
    refresh_token,
  })

  return response.data
}

export const getSpotifyUserPlaylists = async (userId: string) => {
  if (!readSpotifyAuthState().access_token) {
    throw new Error('No Spotify access token available')
  }
  if (!userId.trim()) {
    throw new Error('A Spotify user ID is required')
  }
  const response = await spotifyApi.get<SpotifyPlaylists>(
    `/spotify/users/${encodeURIComponent(userId)}/playlists`,
  )
  return response.data
}
