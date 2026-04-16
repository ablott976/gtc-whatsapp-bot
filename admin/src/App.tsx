import { useState, useEffect } from 'react'
import * as api from './api'

function Login({ onLogin }: { onLogin: () => void }) {
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const data = await api.login(user, pass)
      if (data?.token) { localStorage.setItem('gtc_token', data.token); onLogin() }
      else setError('Credenciales incorrectas')
    } catch { setError('Error de conexion') }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <form onSubmit={submit} className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">GTC WhatsApp Bot</h1>
        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
        <input value={user} onChange={e => setUser(e.target.value)} placeholder="Usuario"
          className="w-full p-2 border rounded mb-3" />
        <input value={pass} onChange={e => setPass(e.target.value)} placeholder="Contrasena" type="password"
          className="w-full p-2 border rounded mb-4" />
        <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">Entrar</button>
      </form>
    </div>
  )
}

function RouteForm({ initial, onSave, onCancel }: { initial?: any; onSave: (d: any) => void; onCancel: () => void }) {
  const [form, setForm] = useState({
    phone: initial?.phone || '',
    company_name: initial?.company_name || '',
    gtc_url: initial?.gtc_url || 'https://demo.gotimecloud.com',
    company: initial?.company || '',
    username: initial?.username || '',
    password: initial?.password || '',
    gtc_utc: initial?.gtc_utc ?? 2,
    language: initial?.language || 'es',
  })

  const set = (k: string, v: any) => setForm({ ...form, [k]: v })

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-6">
      <h3 className="text-lg font-semibold mb-4">{initial ? 'Editar' : 'Nueva'} Ruta</h3>
      <div className="grid grid-cols-2 gap-4">
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Telefono WhatsApp</label>
          <input value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="34600000000"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Nombre Empresa</label>
          <input value={form.company_name} onChange={e => set('company_name', e.target.value)} placeholder="Mi Empresa SL"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">URL GoTimeCloud</label>
          <input value={form.gtc_url} onChange={e => set('gtc_url', e.target.value)}
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Company Code</label>
          <input value={form.company} onChange={e => set('company', e.target.value)} placeholder="demo"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Usuario GTC</label>
          <input value={form.username} onChange={e => set('username', e.target.value)} placeholder="admin"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Contrasena GTC</label>
          <input value={form.password} onChange={e => set('password', e.target.value)} type="password"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">UTC Offset</label>
          <input value={form.gtc_utc} onChange={e => set('gtc_utc', parseInt(e.target.value))} type="number"
            className="w-full p-2 border rounded" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Idioma</label>
          <select value={form.language} onChange={e => set('language', e.target.value)} className="w-full p-2 border rounded">
            <option value="es">Espanol</option><option value="en">English</option><option value="pt">Portugues</option>
          </select></div>
      </div>
      <div className="flex gap-3 mt-4">
        <button onClick={() => onSave(form)} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {initial ? 'Guardar' : 'Crear'}</button>
        <button onClick={onCancel} className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400">Cancelar</button>
      </div>
    </div>
  )
}

function RouteTable({ routes, onEdit, onDelete, onToggle }: any) {
  if (!routes?.length) return <p className="text-gray-500 text-center py-8">No hay rutas configuradas. Crea la primera.</p>

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50"><tr>
          <th className="p-3 text-left text-sm font-medium text-gray-700">Telefono</th>
          <th className="p-3 text-left text-sm font-medium text-gray-700">Empresa</th>
          <th className="p-3 text-left text-sm font-medium text-gray-700">URL GTC</th>
          <th className="p-3 text-left text-sm font-medium text-gray-700">Company</th>
          <th className="p-3 text-left text-sm font-medium text-gray-700">UTC</th>
          <th className="p-3 text-left text-sm font-medium text-gray-700">Estado</th>
          <th className="p-3 text-right text-sm font-medium text-gray-700">Acciones</th>
        </tr></thead>
        <tbody>
          {routes.map((r: any) => (
            <tr key={r.id} className="border-t hover:bg-gray-50">
              <td className="p-3 font-mono text-sm">{r.phone}</td>
              <td className="p-3">{r.company_name}</td>
              <td className="p-3 text-sm text-gray-500 truncate max-w-48">{r.gtc_url}</td>
              <td className="p-3 font-mono text-sm">{r.company}</td>
              <td className="p-3 text-center">+{r.gtc_utc || 2}</td>
              <td className="p-3">
                <button onClick={() => onToggle(r)}
                  className={`px-2 py-1 rounded text-xs ${r.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {r.active ? 'Activo' : 'Inactivo'}
                </button>
              </td>
              <td className="p-3 text-right">
                <button onClick={() => onEdit(r)} className="text-blue-600 hover:text-blue-800 mr-3 text-sm">Editar</button>
                <button onClick={() => onDelete(r.id)} className="text-red-600 hover:text-red-800 text-sm">Eliminar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Stats({ stats }: { stats: any }) {
  if (!stats) return null
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="bg-white p-4 rounded-lg shadow"><p className="text-2xl font-bold">{stats.total_routes}</p><p className="text-gray-500 text-sm">Rutas totales</p></div>
      <div className="bg-white p-4 rounded-lg shadow"><p className="text-2xl font-bold text-green-600">{stats.active_routes}</p><p className="text-gray-500 text-sm">Activas</p></div>
      <div className="bg-white p-4 rounded-lg shadow"><p className="text-2xl font-bold text-blue-600">{stats.messages_today}</p><p className="text-gray-500 text-sm">Mensajes hoy</p></div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('gtc_token'))
  const [routes, setRoutes] = useState([])
  const [stats, setStats] = useState<any>(null)
  const [editing, setEditing] = useState<any>(null)
  const [showForm, setShowForm] = useState(false)

  const load = async () => {
    try {
      const [r, s] = await Promise.all([api.getRoutes(), api.getStats()])
      if (r) setRoutes(r)
      if (s) setStats(s)
    } catch {}
  }

  useEffect(() => { if (authed) load() }, [authed])

  if (!authed) return <Login onLogin={() => setAuthed(true)} />

  const saveRoute = async (data: any) => {
    try {
      if (editing) await api.updateRoute(editing.id, data)
      else await api.createRoute(data)
      setShowForm(false); setEditing(null); load()
    } catch (e: any) { alert('Error: ' + e.message) }
  }

  const removeRoute = async (id: number) => {
    if (!confirm('Eliminar esta ruta?')) return
    try { await api.deleteRoute(id); load() } catch {}
  }

  const toggleRoute = async (r: any) => {
    try { await api.updateRoute(r.id, { active: !r.active }); load() } catch {}
  }

  const logout = () => { localStorage.removeItem('gtc_token'); setAuthed(false) }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-sm"><div className="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
        <h1 className="text-xl font-bold text-gray-800">GTC WhatsApp Bot</h1>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">Salir</button>
      </div></nav>
      <div className="max-w-5xl mx-auto px-4 py-6">
        <Stats stats={stats} />
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Routing de WhatsApp</h2>
          <button onClick={() => { setEditing(null); setShowForm(true) }}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">+ Nueva Ruta</button>
        </div>
        {showForm && <RouteForm initial={editing} onSave={saveRoute} onCancel={() => { setShowForm(false); setEditing(null) }} />}
        <RouteTable routes={routes} onEdit={(r: any) => { setEditing(r); setShowForm(true) }}
          onDelete={removeRoute} onToggle={toggleRoute} />
      </div>
    </div>
  )
}
