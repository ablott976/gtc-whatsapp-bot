const API = '/admin/api'

async function api(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('gtc_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.headers as Record<string, string>) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API}${path}`, { ...opts, headers })
  if (res.status === 401) { localStorage.removeItem('gtc_token'); window.location.reload(); return null }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
  return res.json()
}

export const login = (username: string, password: string) => api('/login', { method: 'POST', body: JSON.stringify({ username, password }) })
export const getRoutes = () => api('/routes')
export const createRoute = (data: any) => api('/routes', { method: 'POST', body: JSON.stringify(data) })
export const updateRoute = (id: number, data: any) => api(`/routes/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteRoute = (id: number) => api(`/routes/${id}`, { method: 'DELETE' })
export const getStats = () => api('/stats')
export const getMessages = (phone?: string) => api(`/messages${phone ? `?phone=${phone}` : ''}`)
