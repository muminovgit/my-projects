// Instagram Graph API proxy. Keeps the access token on the server.
// Env vars (Netlify → Site settings → Environment variables):
//   IG_ACCESS_TOKEN  long-lived token of an Instagram Business/Creator account
//   IG_USER_ID       that account's Instagram user id
// Search:  ?q=#hashtag  → top media for hashtag
//          ?q=username  → business/creator account profile + recent media

const GRAPH = 'https://graph.facebook.com/v21.0'
const MEDIA_FIELDS = 'id,caption,media_type,media_url,thumbnail_url,permalink,like_count,comments_count'

const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60' },
  })

async function graph(path, params) {
  const url = new URL(`${GRAPH}${path}`)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  url.searchParams.set('access_token', process.env.IG_ACCESS_TOKEN)
  const res = await fetch(url)
  const data = await res.json()
  if (!res.ok) throw new Error(data?.error?.message ?? `Instagram API error ${res.status}`)
  return data
}

export default async (req) => {
  const token = process.env.IG_ACCESS_TOKEN
  const userId = process.env.IG_USER_ID
  if (!token || !userId) {
    return json(500, { error: 'IG_ACCESS_TOKEN va IG_USER_ID sozlanmagan' })
  }

  const q = (new URL(req.url).searchParams.get('q') ?? '').trim()
  if (!q) return json(400, { error: 'Qidiruv so‘zi kiritilmagan' })
  if (q.length > 100) return json(400, { error: 'Qidiruv juda uzun' })

  try {
    if (q.startsWith('#')) {
      const tag = q.slice(1).replace(/\s+/g, '')
      if (!tag) return json(400, { error: 'Hashtag bo‘sh' })
      const found = await graph('/ig_hashtag_search', { user_id: userId, q: tag })
      const hashtagId = found.data?.[0]?.id
      if (!hashtagId) return json(200, { type: 'hashtag', query: tag, media: [] })
      const media = await graph(`/${hashtagId}/top_media`, {
        user_id: userId,
        fields: MEDIA_FIELDS,
        limit: '24',
      })
      return json(200, { type: 'hashtag', query: tag, media: media.data ?? [] })
    }

    const username = q.replace(/^@/, '').replace(/[^\w.]/g, '')
    if (!username) return json(400, { error: 'Username noto‘g‘ri' })
    const data = await graph(`/${userId}`, {
      fields: `business_discovery.username(${username}){username,name,biography,profile_picture_url,followers_count,media_count,media.limit(12){${MEDIA_FIELDS}}}`,
    })
    const p = data.business_discovery
    return json(200, {
      type: 'user',
      query: username,
      profile: {
        username: p.username,
        name: p.name,
        biography: p.biography,
        picture: p.profile_picture_url,
        followers: p.followers_count,
        posts: p.media_count,
      },
      media: p.media?.data ?? [],
    })
  } catch (err) {
    return json(502, { error: err instanceof Error ? err.message : 'Noma’lum xato' })
  }
}
