import { useQuery, useQueryClient } from '@tanstack/react-query'

export type SpotifyProfile = Record<string, unknown>

export type SpotifyAuthState = {
  access_token: string | null
  refresh_token: string | null
  token_type: string | null
  expires_in: string | null
  scope: string | null
  profile: SpotifyProfile | null
}

export const SPOTIFY_AUTH_QUERY_KEY = ['spotifyAuth']

export const EMPTY_AUTH_STATE: SpotifyAuthState = {
  access_token: null,
  refresh_token: null,
  token_type: null,
  expires_in: null,
  scope: null,
  profile: null,
}

let inMemorySpotifyAuthState: SpotifyAuthState = EMPTY_AUTH_STATE

export const readSpotifyAuthState = (): SpotifyAuthState => {
  //empty state if not set
  return inMemorySpotifyAuthState
}

export const saveSpotifyAuthState = (
  authState: Partial<SpotifyAuthState>,
): SpotifyAuthState => {
  inMemorySpotifyAuthState = {
    ...EMPTY_AUTH_STATE,
    ...inMemorySpotifyAuthState,
    ...authState,
  }
  return inMemorySpotifyAuthState
}

export const clearSpotifyAuthState = (): SpotifyAuthState => {
  inMemorySpotifyAuthState = EMPTY_AUTH_STATE
  return inMemorySpotifyAuthState
}

export const useSpotifyAuth = () => {
  return useQuery({
    queryKey: SPOTIFY_AUTH_QUERY_KEY,
    queryFn: readSpotifyAuthState,
    initialData: readSpotifyAuthState(),
    staleTime: Infinity,
  })
}

export const useSpotifyAuthActions = () => {
  const queryClient = useQueryClient()

  const setAuth = (authState: Partial<SpotifyAuthState>) => {
    const nextState = saveSpotifyAuthState(authState)
    queryClient.setQueryData(SPOTIFY_AUTH_QUERY_KEY, nextState)
    return nextState
  }

  const clearAuth = () => {
    const nextState = clearSpotifyAuthState()
    queryClient.setQueryData(SPOTIFY_AUTH_QUERY_KEY, nextState)
    return nextState
  }

  return { setAuth, clearAuth }
}
