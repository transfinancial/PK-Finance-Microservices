const BASE = 'https://api.fintraxa.com'

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export const api = {
  health:        ()  => request('/api/health'),

  // MUFAP
  getFunds:      (p) => request(`/api/mufap/funds?${new URLSearchParams(p || {})}`),
  searchFunds:   (q) => request(`/api/mufap/funds/search?q=${encodeURIComponent(q)}`),
  getFundStats:  ()  => request('/api/mufap/funds/stats'),
  getCategories: ()  => request('/api/mufap/funds/categories'),
  getTopNav:     (n) => request(`/api/mufap/funds/top-nav?limit=${n || 20}`),
  scrapeFunds:   ()  => request('/api/mufap/scrape/sync', { method: 'POST' }),

  // PSX
  getStocks:     (p) => request(`/api/psx/stocks?${new URLSearchParams(p || {})}`),
  searchStocks:  (q) => request(`/api/psx/stocks/search?symbol=${encodeURIComponent(q)}`),
  getGainers:    (n) => request(`/api/psx/stocks/gainers?limit=${n || 20}`),
  getLosers:     (n) => request(`/api/psx/stocks/losers?limit=${n || 20}`),
  getActive:     (n) => request(`/api/psx/stocks/active?limit=${n || 20}`),
  getSummary:    ()  => request('/api/psx/stocks/summary'),
  getIndices:    ()  => request('/api/psx/indices'),
  scrapeStocks:  ()  => request('/api/psx/scrape/sync', { method: 'POST' }),
  scrapeIndices: ()  => request('/api/psx/scrape/indices', { method: 'POST' }),
}
