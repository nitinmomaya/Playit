// Use the shared request/state cache.
import { useQuery, useQueryClient } from '@tanstack/react-query'
// Use React state/lifecycle APIs.
import { useCallback } from 'react'

// Describe the SpotifyProfile data contract.
export type SpotifyProfile = Record<string, unknown>

// Describe the SpotifyAuthState data contract.
export type SpotifyAuthState = {
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
  profile: SpotifyProfile | null
}

// Prepare SPOTIFY_AUTH_QUERY_KEY for the following operation.
export const SPOTIFY_AUTH_QUERY_KEY = ['spotifyAuth']

// Prepare EMPTY_AUTH_STATE for the following operation.
export const EMPTY_AUTH_STATE: SpotifyAuthState = {
  // Set the access_token option/value.
  access_token: null,
  // Set the refresh_token option/value.
  refresh_token: null,
  // Set the token_type option/value.
  token_type: null,
  // Set the expires_in option/value.
  expires_in: null,
  // Set the scope option/value.
  scope: null,
  // Set the profile option/value.
  profile: null,
}

// Prepare inMemorySpotifyAuthState for the following operation.
let inMemorySpotifyAuthState: SpotifyAuthState = EMPTY_AUTH_STATE

// Define the readSpotifyAuthState handler/helper.
export const readSpotifyAuthState = (): SpotifyAuthState => {
  //empty state if not set
  return inMemorySpotifyAuthState
}

// Define the saveSpotifyAuthState handler/helper.
export const saveSpotifyAuthState = (
  authState: Partial<SpotifyAuthState>,
): SpotifyAuthState => {
  inMemorySpotifyAuthState = {
    ...EMPTY_AUTH_STATE,
    ...inMemorySpotifyAuthState,
    ...authState,
  }
  // Return the current operation's result.
  return inMemorySpotifyAuthState
}

// Define the clearSpotifyAuthState handler/helper.
export const clearSpotifyAuthState = (): SpotifyAuthState => {
  inMemorySpotifyAuthState = EMPTY_AUTH_STATE
  // Return the current operation's result.
  return inMemorySpotifyAuthState
}

// Configure cached useSpotifyAuth data.
export const useSpotifyAuth = () => {
  // Return the current operation's result.
  return useQuery({
    // Set the queryKey option/value.
    queryKey: SPOTIFY_AUTH_QUERY_KEY,
    // Set the queryFn option/value.
    queryFn: readSpotifyAuthState,
    // Set the initialData option/value.
    initialData: readSpotifyAuthState(),
    // Set the staleTime option/value.
    staleTime: Infinity,
  })
}

// Configure cached useSpotifyAuthActions data.
export const useSpotifyAuthActions = () => {
  // Configure cached queryClient data.
  const queryClient = useQueryClient()

  // Define the setAuth handler/helper.
  const setAuth = useCallback((authState: Partial<SpotifyAuthState>) => {
    // Prepare nextState for the following operation.
    const nextState = saveSpotifyAuthState(authState)
    // Notify subscribers of the updated cached auth state.
    queryClient.setQueryData(SPOTIFY_AUTH_QUERY_KEY, nextState)
    // Return the current operation's result.
    return nextState
  }, [queryClient])

  // Define the clearAuth handler/helper.
  const clearAuth = useCallback(() => {
    // Prepare nextState for the following operation.
    const nextState = clearSpotifyAuthState()
    // Notify subscribers of the updated cached auth state.
    queryClient.setQueryData(SPOTIFY_AUTH_QUERY_KEY, nextState)
    // Return the current operation's result.
    return nextState
  }, [queryClient])

  // Return the current operation's result.
  return { setAuth, clearAuth }
}

/* File summary
 * - Stores Spotify tokens/profile in memory and mirrors them into Query.
 * - Exports read/save/clear helpers and reactive auth hooks.
 * - Does not persist tokens across a full reload.
 */
