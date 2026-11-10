import { useState, type FormEvent } from 'react'
import { Search, X } from 'lucide-react'

type Media = {
  id: string
  caption?: string
  media_type: string
  media_url?: string
  thumbnail_url?: string
  permalink: string
}

type Profile = {
  username: string
  name?: string
  biography?: string
  picture?: string
  followers?: number
  posts?: number
}

type Result = { type: 'user' | 'hashtag'; query: string; profile?: Profile; media: Media[] }

export default function InstagramSearch({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Result | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(
        `/.netlify/functions/instagram-search?q=${encodeURIComponent(q.trim())}`,
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Xatolik')
      setResult(data)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Xatolik')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center p-4 pt-20"
      onClick={onClose}
    >
      <div
        className="liquid-glass rounded-xl w-full max-w-3xl max-h-[80vh] overflow-y-auto p-5 text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <form onSubmit={submit} className="flex-1 flex items-center gap-2">
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="@username yoki #hashtag"
              className="flex-1 bg-white/10 rounded-lg px-4 py-2 text-sm outline-none placeholder:text-gray-400"
            />
            <button
              type="submit"
              disabled={loading}
              aria-label="Qidirish"
              className="bg-white text-black rounded-lg p-2 disabled:opacity-50"
            >
              <Search size={18} />
            </button>
          </form>
          <button type="button" onClick={onClose} aria-label="Yopish">
            <X size={20} />
          </button>
        </div>

        {loading && <p className="mt-4 text-sm text-gray-300">Qidirilmoqda…</p>}
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        {result?.profile && (
          <div className="mt-5 flex items-center gap-4">
            {result.profile.picture && (
              <img src={result.profile.picture} alt="" className="w-16 h-16 rounded-full" />
            )}
            <div className="text-sm">
              <div className="font-medium">@{result.profile.username}</div>
              <div className="text-gray-300">
                {result.profile.followers?.toLocaleString()} followers ·{' '}
                {result.profile.posts?.toLocaleString()} posts
              </div>
              {result.profile.biography && (
                <div className="text-gray-400 mt-1">{result.profile.biography}</div>
              )}
            </div>
          </div>
        )}

        {result && result.media.length === 0 && (
          <p className="mt-4 text-sm text-gray-300">Hech narsa topilmadi.</p>
        )}

        {result && result.media.length > 0 && (
          <div className="mt-5 grid grid-cols-2 sm:grid-cols-3 gap-2">
            {result.media.map((m) => {
              const src = m.thumbnail_url ?? m.media_url
              return (
                <a
                  key={m.id}
                  href={m.permalink}
                  target="_blank"
                  rel="noreferrer"
                  className="block aspect-square bg-white/10 rounded-lg overflow-hidden"
                  title={m.caption}
                >
                  {src && <img src={src} alt="" className="w-full h-full object-cover" />}
                </a>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
