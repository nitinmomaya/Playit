import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

export type YouTubeProfile = {
  sub: string
  name?: string
  email?: string
  picture?: string
}

export type YouTubeAuthState = {
  access_token: string | null
  refresh_token: string | null
  token_type: string | null
  expires_in: string | null
  scope: string | null
  profile: YouTubeProfile | null
}

const YOUTUBE_AUTH_QUERY_KEY = ['youtubeAuth']
const EMPTY_AUTH_STATE: YouTubeAuthState = {
  access_token: null, refresh_token: null, token_type: null,
  expires_in: null, scope: null, profile: null,
}
let inMemoryYouTubeAuthState: YouTubeAuthState = { ...EMPTY_AUTH_STATE }

export const readYouTubeAuthState = () => inMemoryYouTubeAuthState

export const useYouTubeAuth = () => useQuery({
  queryKey: YOUTUBE_AUTH_QUERY_KEY,
  queryFn: readYouTubeAuthState,
  initialData: readYouTubeAuthState(),
  staleTime: Infinity,
})

export const useYouTubeAuthActions = () => {
  const queryClient = useQueryClient()
  const setAuth = useCallback((state: Partial<YouTubeAuthState>) => {
    inMemoryYouTubeAuthState = { ...inMemoryYouTubeAuthState, ...state }
    queryClient.setQueryData(YOUTUBE_AUTH_QUERY_KEY, inMemoryYouTubeAuthState)
  }, [queryClient])
  const clearAuth = useCallback(() => {
    inMemoryYouTubeAuthState = { ...EMPTY_AUTH_STATE }
    queryClient.setQueryData(YOUTUBE_AUTH_QUERY_KEY, inMemoryYouTubeAuthState)
    queryClient.removeQueries({ queryKey: ['youtubePlaylists'] })
    queryClient.removeQueries({ queryKey: ['youtubeChannels'] })
  }, [queryClient])
  return { setAuth, clearAuth }
}