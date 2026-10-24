import { useState } from 'react'
import { isAxiosError } from 'axios'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useYouTubeAuth, useYouTubeAuthActions } from '../../src/lib/youtubeAuth'
import { getYouTubeChannels, getYouTubePlaylists, refreshYouTubeToken, youtubeApi } from '../../src/lib/youtubeApi'
import './index.css'

const libraryError = (error: unknown): string => {
  if (isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (!error.response) return 'Cannot reach the backend. Check the API server and CORS configuration.'
    return `YouTube library request failed (HTTP ${error.response.status}).`
  }
  return 'Could not load the YouTube library. Please reconnect and retry.'
}

const YouTubeLibrary = () => {
  const { data: auth } = useYouTubeAuth()
  const { setAuth } = useYouTubeAuthActions()
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const channels = useQuery({
    queryKey: ['youtubeChannels', auth?.profile?.sub],
    queryFn: ({ signal }) => getYouTubeChannels(signal), retry: false,
  })
  const playlists = useInfiniteQuery({
    queryKey: ['youtubePlaylists', auth?.profile?.sub],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) => getYouTubePlaylists(pageParam, signal),
    getNextPageParam: (lastPage) => lastPage.nextPageToken,
    retry: false,
  })
  const refresh = async () => {
    setRefreshing(true)
    setRefreshError(null)
    try {
      const tokens = await refreshYouTubeToken()
      setAuth({
        ...tokens, expires_in: String(tokens.expires_in),
        refresh_token: tokens.refresh_token ?? auth?.refresh_token ?? null,
      })
      await Promise.all([channels.refetch(), playlists.refetch()])
    } catch {
      setRefreshError('Could not refresh access. Please reconnect your YouTube account.')
    } finally {
      setRefreshing(false)
    }
  }
  const items = playlists.data?.pages.flatMap((page) => page.items) ?? []
  return (
    <section className="youtube-library" aria-label="YouTube library">
      <header>
        <p className="youtube-eyebrow">YOUTUBE · CONNECTED</p>
        <h1>Welcome, {auth?.profile?.name ?? 'music lover'}</h1>
        <p>Your YouTube account and playlists, all in one place.</p>
      </header>
      <div className="youtube-notice">
        <strong>Read-only connection</strong>
        <p>YouTube playlist creation and AI music matching are not available yet. Your Spotify workflow remains unchanged.</p>
      </div>
      {channels.data && <p>{channels.data.items.length
        ? `Channel: ${channels.data.items.map((channel) => channel.snippet.title).join(', ')}`
        : 'No YouTube channel is available for this account. You can create one on YouTube.'}</p>}
      <div className="youtube-actions">
        <button type="button" onClick={() => { window.location.href = `${youtubeApi.defaults.baseURL}/login` }}>Reconnect YouTube</button>
        {auth?.refresh_token && <button type="button" onClick={() => { void refresh() }} disabled={refreshing || playlists.isFetching || channels.isFetching}>
          {refreshing ? 'Refreshing…' : 'Refresh access'}
        </button>}
      </div>
      {channels.isError && <p role="alert">Channel: {libraryError(channels.error)}</p>}
      {playlists.isError && <p role="alert">Playlists: {libraryError(playlists.error)}</p>}
      {refreshError && <p role="alert">{refreshError}</p>}
      <h2>Your playlists</h2>
      {playlists.isPending && <p role="status">Loading playlists…</p>}
      {playlists.isSuccess && !items.length && <p>No playlists found for this account.</p>}
      <ul className="youtube-playlists">
        {items.map((playlist) => <li key={playlist.id}>
          <h3><a href={`https://www.youtube.com/playlist?list=${encodeURIComponent(playlist.id)}`} target="_blank" rel="noopener noreferrer">{playlist.snippet.title}</a></h3>
          <p>{playlist.contentDetails?.itemCount ?? 0} videos</p>
          {playlist.snippet.description && <p>{playlist.snippet.description}</p>}
        </li>)}
      </ul>
      {playlists.hasNextPage && <button type="button" disabled={playlists.isFetchingNextPage} onClick={() => { void playlists.fetchNextPage() }}>
        {playlists.isFetchingNextPage ? 'Loading…' : 'Load more playlists'}
      </button>}
    </section>
  )
}

export default YouTubeLibrary