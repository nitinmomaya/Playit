// Use React state/lifecycle APIs.
import { useState } from 'react'
// Make JSON requests through Axios.
import { isAxiosError } from 'axios'
// Use the shared request/state cache.
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
// Import youtubeAuth dependencies.
import { useYouTubeAuth, useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
// Import youtubeApi dependencies.
import { getYouTubeChannels, getYouTubePlaylists, refreshYouTubeToken, youtubeApi } from '../../src/lib/youtubeApi'
// Import index.css dependencies.
import './index.css'

// Define the libraryError handler/helper.
const libraryError = (error: unknown): string => {
  // Check isAxiosError(error).
  if (isAxiosError(error)) {
    // Prepare detail for the following operation.
    const detail: unknown = error.response?.data?.detail
    // Check typeof detail === 'string'.
    if (typeof detail === 'string') return detail
    // Check !error.response.
    if (!error.response) return 'Cannot reach the backend. Check the API server and CORS configuration.'
    // Return the current operation's result.
    return `YouTube library request failed (HTTP ${error.response.status}).`
  }
  // Return the current operation's result.
  return 'Could not load the YouTube library. Please reconnect and retry.'
}

// Track YouTubeLibrary in component state.
const YouTubeLibrary = () => {
  // Prepare { data: auth } for the following operation.
  const { data: auth } = useYouTubeAuth()
  // Prepare { setAuth } for the following operation.
  const { setAuth } = useYouTubeAuthActions()
  // Track [refreshing, setRefreshing] in component state.
  const [refreshing, setRefreshing] = useState(false)
  // Track [refreshError, setRefreshError] in component state.
  const [refreshError, setRefreshError] = useState<string | null>(null)
  // Configure cached channels data.
  const channels = useQuery({
    // Set the queryKey option/value.
    queryKey: ['youtubeChannels', auth?.profile?.sub],
    // Set the queryFn option/value.
    queryFn: ({ signal }) => getYouTubeChannels(signal), retry: false,
  })
  // Configure cached playlists data.
  const playlists = useInfiniteQuery({
    // Set the queryKey option/value.
    queryKey: ['youtubePlaylists', auth?.profile?.sub],
    // Set the initialPageParam option/value.
    initialPageParam: undefined as string | undefined,
    // Set the queryFn option/value.
    queryFn: ({ pageParam, signal }) => getYouTubePlaylists(pageParam, signal),
    // Set the getNextPageParam option/value.
    getNextPageParam: (lastPage) => lastPage.nextPageToken,
    // Set the retry option/value.
    retry: false,
  })
  // Define the refresh handler/helper.
  const refresh = async () => {
    // Call setRefreshing.
    setRefreshing(true)
    // Call setRefreshError.
    setRefreshError(null)
    // Handle request failures and cleanup below.
    try {
      // Prepare tokens for the following operation.
      const tokens = await refreshYouTubeToken()
      // Call setAuth.
      setAuth({
        ...tokens, expires_in: String(tokens.expires_in),
        // Set the refresh_token option/value.
        refresh_token: tokens.refresh_token ?? auth?.refresh_token ?? null,
      })
      // Call Promise.all.
      await Promise.all([channels.refetch(), playlists.refetch()])
    } catch {
      // Call setRefreshError.
      setRefreshError('Could not refresh access. Please reconnect your YouTube account.')
    } finally {
      // Call setRefreshing.
      setRefreshing(false)
    }
  }
  // Define the items handler/helper.
  const items = playlists.data?.pages.flatMap((page) => page.items) ?? []
  // Return the current operation's result.
  return (
    // Render section.
    <section className="youtube-library" aria-label="YouTube library">
      {/* Render header. */}
      <header>
        {/* Render p. */}
        <p className="youtube-eyebrow">YOUTUBE · CONNECTED</p>
        {/* Render h1. */}
        <h1>Welcome, {auth?.profile?.name ?? 'music lover'}</h1>
        {/* Render p. */}
        <p>Your YouTube account and playlists, all in one place.</p>
      </header>
      {/* Render div. */}
      <div className="youtube-notice">
        {/* Render strong. */}
        <strong>Read-only connection</strong>
        {/* Render p. */}
        <p>YouTube playlist creation and AI music matching are not available yet. Your Spotify workflow remains unchanged.</p>
      </div>
      {/* Render one entry for each item. */}
      {channels.data && <p>{channels.data.items.length
        ? `Channel: ${channels.data.items.map((channel) => channel.snippet.title).join(', ')}`
        : 'No YouTube channel is available for this account. You can create one on YouTube.'}</p>}
      {/* Render div. */}
      <div className="youtube-actions">
        {/* Render button and handle onClick. */}
        <button type="button" onClick={() => { window.location.href = `${youtubeApi.defaults.baseURL}/login` }}>Reconnect YouTube</button>
        {/* Render the matching state/condition only. */}
        {auth?.refresh_token && <button type="button" onClick={() => { void refresh() }} disabled={refreshing || playlists.isFetching || channels.isFetching}>
          {/* Render the matching state/condition only. */}
          {refreshing ? 'Refreshing…' : 'Refresh access'}
        </button>}
      </div>
      {/* Render the matching state/condition only. */}
      {channels.isError && <p role="alert">Channel: {libraryError(channels.error)}</p>}
      {/* Render the matching state/condition only. */}
      {playlists.isError && <p role="alert">Playlists: {libraryError(playlists.error)}</p>}
      {/* Render the matching state/condition only. */}
      {refreshError && <p role="alert">{refreshError}</p>}
      {/* Render h2. */}
      <h2>Your playlists</h2>
      {/* Render the matching state/condition only. */}
      {playlists.isPending && <p role="status">Loading playlists…</p>}
      {/* Render the matching state/condition only. */}
      {playlists.isSuccess && !items.length && <p>No playlists found for this account.</p>}
      {/* Render ul. */}
      <ul className="youtube-playlists">
        {/* Render one entry for each item. */}
        {items.map((playlist) => <li key={playlist.id}>
          {/* Render h3. */}
          <h3><a href={`https://www.youtube.com/playlist?list=${encodeURIComponent(playlist.id)}`} target="_blank" rel="noopener noreferrer">{playlist.snippet.title}</a></h3>
          {/* Render p. */}
          <p>{playlist.contentDetails?.itemCount ?? 0} videos</p>
          {/* Render the matching state/condition only. */}
          {playlist.snippet.description && <p>{playlist.snippet.description}</p>}
        </li>)}
      </ul>
      {/* Render the matching state/condition only. */}
      {playlists.hasNextPage && <button type="button" disabled={playlists.isFetchingNextPage} onClick={() => { void playlists.fetchNextPage() }}>
        {/* Render the matching state/condition only. */}
        {playlists.isFetchingNextPage ? 'Loading…' : 'Load more playlists'}
      </button>}
    </section>
  )
}

// Export this module's public entry point.
export default YouTubeLibrary

/* File summary
 * - Provides the older channel/playlist library view with manual refresh.
 * - Loads additional playlist pages through TanStack Query.
 * - Is not mounted by the active Home chat page; its read-only notice is legacy.
 */
