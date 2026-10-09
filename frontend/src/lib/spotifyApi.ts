import axios, { AxiosHeaders, type RawAxiosRequestHeaders } from 'axios'

import { readSpotifyAuthState } from './auth'

export const spotifyApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getSpotifyAuthHeaders = (): RawAxiosRequestHeaders => {
  const { access_token, refresh_token } = readSpotifyAuthState()

  return {
    ...(access_token ? { Authorization: `Bearer ${access_token}` } : {}),
    ...(refresh_token ? { 'X-Refresh-Token': refresh_token } : {}),
  }
}

spotifyApi.interceptors.request.use((config) => {
  const { access_token, refresh_token } = readSpotifyAuthState()

  config.headers = new AxiosHeaders(config.headers ?? {})

  if (access_token) {
    config.headers.set('Authorization', `Bearer ${access_token}`)
  }

  if (refresh_token) {
    config.headers.set('X-Refresh-Token', refresh_token)
  }

  return config
})

export const getSpotifyUser = async () => {
  const { access_token } = readSpotifyAuthState()

  if (!access_token) {
    throw new Error('No Spotify access token available')
  }

  const response = await spotifyApi.get('/me', {
    headers: getSpotifyAuthHeaders(),
  })

  return response.data
}

export const refreshSpotifyToken = async () => {
  const { refresh_token } = readSpotifyAuthState()

  if (!refresh_token) {
    throw new Error('No Spotify refresh token available')
  }

  const response = await axios.post(
    'http://localhost:8000/spotify/refresh',
    {
      refresh_token,
    },
    {
      headers: {
        'Content-Type': 'application/json',
      },
    },
  )

  return response.data
}
