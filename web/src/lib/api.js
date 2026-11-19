// REST-клієнт браузера. Токен зберігається у sessionStorage (живе до закриття вкладки).

const KEY = 'cloudfolder.session'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY)) || null
  } catch {
    return null
  }
}

export const session = {
  current: loadSession(),
  set(value) {
    this.current = value
    try {
      if (value) sessionStorage.setItem(KEY, JSON.stringify(value))
      else sessionStorage.removeItem(KEY)
    } catch {
      /* приватний режим — працюємо без збереження */
    }
  },
}

async function request(path, { method = 'GET', json, body, raw = false } = {}) {
  const headers = {}
  if (session.current) headers.Authorization = `Bearer ${session.current.token}`
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  }
  let resp
  try {
    resp = await fetch(path, { method, headers, body })
  } catch (e) {
    throw new ApiError('Сервер недоступний', 0)
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const data = await resp.json()
      detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join('; ') : data.detail || detail
    } catch {
      /* тіло без JSON */
    }
    if (resp.status === 401 && session.current) session.set(null)
    throw new ApiError(detail, resp.status)
  }
  if (raw) return resp
  return resp.status === 204 ? null : resp.json()
}

async function auth(path, username, password) {
  const data = await request(path, { method: 'POST', json: { username, password } })
  session.set({ token: data.access_token, username: data.username })
  return data.username
}

export const api = {
  register: (u, p) => auth('/api/auth/register', u, p),
  login: (u, p) => auth('/api/auth/login', u, p),
  logout: () => session.set(null),
  listFiles: () => request('/api/files'),
  upload(file, name = file.name) {
    const form = new FormData()
    form.append('file', file, name)
    form.append('name', name)
    return request('/api/files', { method: 'POST', body: form })
  },
  async download(id) {
    return (await request(`/api/files/${id}/content?download=true`, { raw: true })).blob()
  },
  remove: (id) => request(`/api/files/${id}`, { method: 'DELETE' }),
}
