// Use React state/lifecycle APIs.
import { useCallback } from 'react'
// Use the shared request/state cache.
import { useQuery, useQueryClient } from '@tanstack/react-query'

// Describe the YouTubeProfile data contract.
export type YouTubeProfile = {
  // Define sub in this data shape.
  sub: string
  // Define name in this data shape.
  name?: string
  // Define email in this data shape.
  email?: string
  // Define picture in this data shape.
  picture?: string
}

// Describe the YouTubeAuthState data contract.
export type YouTubeAuthState = {
  // Define access_token in this data shape.
  access_token: string | null
  // Define refresh_token in this data shape.
  refresh_token: string | null
  // Define token_type in this data shape.
  token_type: string | null
  // Define expires_in in this data shape.
  expires_in: string | null
  // Define scope in this data shape.
  scope: string | null
  // Define profile in this data shape.
  profile: YouTubeProfile | null
}

// Prepare YOUTUBE_AUTH_QUERY_KEY for the following operation.
const YOUTUBE_AUTH_QUERY_KEY = ['youtubeAuth']
// Prepare EMPTY_AUTH_STATE for the following operation.
const EMPTY_AUTH_STATE: YouTubeAuthState = {
  // Set the access_token option/value.
  access_token: null, refresh_token: null, token_type: null,
  // Set the expires_in option/value.
  expires_in: null, scope: null, profile: null,
}
// Prepare inMemoryYouTubeAuthState for the following operation.
let inMemoryYouTubeAuthState: YouTubeAuthState = { ...EMPTY_AUTH_STATE }

// Define the readYouTubeAuthState handler/helper.
export const readYouTubeAuthState = () => inMemoryYouTubeAuthState

// Configure cached useYouTubeAuth data.
export const useYouTubeAuth = () => useQuery({
  // Set the queryKey option/value.
  queryKey: YOUTUBE_AUTH_QUERY_KEY,
  // Set the queryFn option/value.
  queryFn: readYouTubeAuthState,
  // Set the initialData option/value.
  initialData: readYouTubeAuthState(),
  // Set the staleTime option/value.
  staleTime: Infinity,
})

// Configure cached useYouTubeAuthActions data.
export const useYouTubeAuthActions = () => {
  // Configure cached queryClient data.
  const queryClient = useQueryClient()
  // Define the setAuth handler/helper.
  const setAuth = useCallback((state: Partial<YouTubeAuthState>) => {
    inMemoryYouTubeAuthState = { ...inMemoryYouTubeAuthState, ...state }
    // Notify subscribers of the updated cached auth state.
    queryClient.setQueryData(YOUTUBE_AUTH_QUERY_KEY, inMemoryYouTubeAuthState)
  }, [queryClient])
  // Define the clearAuth handler/helper.
  const clearAuth = useCallback(() => {
    inMemoryYouTubeAuthState = { ...EMPTY_AUTH_STATE }
    // Notify subscribers of the updated cached auth state.
    queryClient.setQueryData(YOUTUBE_AUTH_QUERY_KEY, inMemoryYouTubeAuthState)
    // Call queryClient.removeQueries.
    queryClient.removeQueries({ queryKey: ['youtubePlaylists'] })
    // Call queryClient.removeQueries.
    queryClient.removeQueries({ queryKey: ['youtubeChannels'] })
  }, [queryClient])
  // Return the current operation's result.
  return { setAuth, clearAuth }
}

/* File summary
 * - Keeps Google credentials separate from Spotify state.
 * - Updates the auth cache and clears related library queries on logout.
 */
