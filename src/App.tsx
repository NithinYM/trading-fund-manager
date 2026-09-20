import { lazy, Suspense, useCallback, useEffect, useState } from 'react'

import type { Trading } from './PnlChart'

const PnlChart = lazy(() => import('./PnlChart'))

type Dashboard = {
  total_current_capital: string
  current_month_pnl: string
  total_net_pnl: string
  total_fees: string
  active_clients: number
  today_pnl: string
}

type Client = {
  id: string
  client_code: string
  name: string
  opening_capital: string
  current_balance: string | null
  join_date: string
  contact: string | null
  notes: string | null
  status: string
  fee_type: string
  fee_value: string
  fee_basis: string | null
  fee_start_date: string | null
}

type Readiness = {
  status: string
  database: string
}

type WorkbookPreview = {
  filename: string
  sheets: Array<{ name: string; rows: number; columns: number }>
  mappings: Array<{ sheet: string; recognized: boolean; data_rows: number; errors: string[] }>
}

type DailyAllocation = {
  trading_date: string
  active_capital: string
  active_clients: number
  net_pnl: string
  allocated_pnl: string
  total_fees: string
  manager_fee: string
  allocation_difference: string
  entries: Array<{
    client_id: string
    client_code: string
    client_name: string
    capital: string
    share_percent: string
    allocated_pnl: string
    fee: string
    net_pnl: string
    closing_balance: string
  }>
}

type ManagerAccount = {
  id: string
  code: string
  name: string
  opening_capital: string
  current_balance: string
  fees_received: string
}

type ReconciliationReport = {
  trading_date: string
  net_pnl: string
  allocated_pnl: string
  allocation_delta: string
  total_client_fees: string
  manager_fee_credits: string
  fee_transfer_delta: string
  allocation_reconciled: boolean
  fees_reconciled: boolean
}

type ManagerReconciliation = {
  account_id: string
  code: string
  name: string
  opening_capital: string
  fees_received: string
  expected_client_fees: string
  fee_transfer_delta: string
  current_balance: string
  fees_reconciled: boolean
  trading_date: string | null
}

type ClientDetail = {
  client: Client
  summary: {
    current_capital: string
    total_contributed: string
    total_withdrawn: string
    total_allocated_pnl: string
    total_fees: string
    net_pnl: string
    current_status: string
  }
  status_history: Array<{ id: string; status: string; from_date: string; to_date: string; remarks: string | null }>
  ledger: Array<{ trading_date: string; fund_movement: string; allocated_pnl: string; fee_debited: string; net_client_pnl: string; closing_balance: string; status_on_date: string }>
}

type AuditEntry = {
  id: string
  action: string
  entity_type: string
  timestamp: string | null
}

type LoginResponse = {
  access_token: string
  token_type: string
  role: string
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const currentDateLabel = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
const currentYear = new Date().getFullYear()

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal })
  if (!response.ok) throw new Error(`Unable to load ${path}`)
  return response.json() as Promise<T>
}

function money(value: string | number) {
  return `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [managerAccounts, setManagerAccounts] = useState<ManagerAccount[]>([])
  const [trading, setTrading] = useState<Trading[]>([])
  const [tradingDates, setTradingDates] = useState<string[]>([])
  const [reportDate, setReportDate] = useState(new Date().toISOString().slice(0, 10))
  const [selectedManagerAccountCode, setSelectedManagerAccountCode] = useState('')
  const [reconciliationReport, setReconciliationReport] = useState<ReconciliationReport | null>(null)
  const [managerReconciliation, setManagerReconciliation] = useState<ManagerReconciliation | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [managerReportLoading, setManagerReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')
  const [managerReportError, setManagerReportError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [backendReady, setBackendReady] = useState(false)
  const [showAllClients, setShowAllClients] = useState(false)
  const [workbookPreview, setWorkbookPreview] = useState<WorkbookPreview | null>(null)
  const [selectedWorkbook, setSelectedWorkbook] = useState<File | null>(null)
  const [importError, setImportError] = useState('')
  const [importing, setImporting] = useState(false)
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('trading-fund-access-token') ?? '')
  const [userRole, setUserRole] = useState(() => localStorage.getItem('trading-fund-user-role') ?? '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [signingIn, setSigningIn] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [commitMessage, setCommitMessage] = useState('')
  const [tradingForm, setTradingForm] = useState({ trading_date: new Date().toISOString().slice(0, 10), gross_trading_pnl: '', transaction_charges: '', remarks: '' })
  const [dailyAllocation, setDailyAllocation] = useState<DailyAllocation | null>(null)
  const [tradingError, setTradingError] = useState('')
  const [savingTrading, setSavingTrading] = useState(false)
  const [selectedClientId, setSelectedClientId] = useState('')
  const [editingClientId, setEditingClientId] = useState('')
  const [clientDetail, setClientDetail] = useState<ClientDetail | null>(null)
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([])
  const [adminError, setAdminError] = useState('')
  const [adminMessage, setAdminMessage] = useState('')
  const [adminSaving, setAdminSaving] = useState(false)
  const [clientForm, setClientForm] = useState({ client_code: '', name: '', opening_capital: '', join_date: new Date().toISOString().slice(0, 10), contact: '', notes: '', status: 'ACTIVE', fee_type: 'NONE', fee_value: '0', fee_basis: '', fee_start_date: '' })
  const [statusForm, setStatusForm] = useState({ client_id: '', status: 'ACTIVE', from_date: new Date().toISOString().slice(0, 10), to_date: new Date().toISOString().slice(0, 10), remarks: '' })
  const [movementForm, setMovementForm] = useState({ client_id: '', date: new Date().toISOString().slice(0, 10), movement_type: 'DEPOSIT', amount: '', remarks: '' })

  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError('')
    try {
      const [dashboardResult, clientResult, tradingResult, managerResult, readinessResult] = await Promise.allSettled([
        getJson<Dashboard>('/dashboard', signal),
        getJson<Client[]>('/clients', signal),
        getJson<Trading[]>('/trading', signal),
        getJson<ManagerAccount[]>('/manager-accounts', signal),
        getJson<Readiness>('/health/ready', signal),
      ])

      if (dashboardResult.status !== 'fulfilled' || clientResult.status !== 'fulfilled' || tradingResult.status !== 'fulfilled' || managerResult.status !== 'fulfilled') {
        throw new Error('Portfolio data unavailable')
      }

      setDashboard(dashboardResult.value)
      setClients(clientResult.value)
      setManagerAccounts(managerResult.value)
      setTradingDates(tradingResult.value.map((entry) => entry.trading_date))
      setTrading(tradingResult.value.slice(-8))
      setBackendReady(
        readinessResult.status === 'fulfilled' &&
          readinessResult.value.status === 'ready' &&
          readinessResult.value.database === 'ok',
      )
    } catch (caught) {
      if (signal?.aborted || (caught instanceof DOMException && caught.name === 'AbortError')) return
      setError('Connect the backend to load live fund data.')
      setBackendReady(false)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  const loadReconciliationReport = useCallback(async (date: string) => {
    setReportLoading(true)
    setReportError('')
    try {
      const response = await fetch(`${API_URL}/reports/reconciliation/${date}`)
      if (response.status === 404) {
        setReconciliationReport(null)
        return
      }
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Reconciliation report unavailable')
      }
      const report = await response.json() as ReconciliationReport
      setReconciliationReport(report)
    } catch (caught) {
      setReconciliationReport(null)
      setReportError(caught instanceof Error ? caught.message : 'Unable to load report')
    } finally {
      setReportLoading(false)
    }
  }, [])

  const loadManagerReconciliation = useCallback(async (accountCode: string, date: string) => {
    if (!accountCode) return
    setManagerReportLoading(true)
    setManagerReportError('')
    try {
      const url = date ? `${API_URL}/manager-accounts/${accountCode}/reconciliation?trading_date=${date}` : `${API_URL}/manager-accounts/${accountCode}/reconciliation`
      const response = await fetch(url)
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Manager account reconciliation unavailable')
      }
      const report = await response.json() as ManagerReconciliation
      setManagerReconciliation(report)
    } catch (caught) {
      setManagerReconciliation(null)
      setManagerReportError(caught instanceof Error ? caught.message : 'Unable to load manager reconciliation')
    } finally {
      setManagerReportLoading(false)
    }
  }, [])

  const loadClientDetail = useCallback(async (clientId: string) => {
    if (!clientId) return
    try {
      const detailResponse = await fetch(`${API_URL}/clients/${clientId}/detail`, { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} })
      if (!detailResponse.ok) throw new Error('Client detail unavailable')
      setClientDetail(await detailResponse.json() as ClientDetail)
      if (accessToken) {
        const auditResponse = await fetch(`${API_URL}/audit-logs?entity_type=CLIENT&entity_id=${clientId}`, { headers: { Authorization: `Bearer ${accessToken}` } })
        setAuditEntries(auditResponse.ok ? await auditResponse.json() as AuditEntry[] : [])
      } else {
        setAuditEntries([])
      }
    } catch {
      setClientDetail(null)
      setAuditEntries([])
    }
  }, [accessToken])

  useEffect(() => {
    const controller = new AbortController()
    void loadData(controller.signal)
    return () => controller.abort()
  }, [loadData])

  useEffect(() => {
    if (!accessToken) return
    void (async () => {
      const response = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${accessToken}` } })
      if (!response.ok) {
        localStorage.removeItem('trading-fund-access-token')
        localStorage.removeItem('trading-fund-user-role')
        setAccessToken('')
        setUserRole('')
        return
      }
      const currentUser = await response.json() as { role: string }
      localStorage.setItem('trading-fund-user-role', currentUser.role)
      setUserRole(currentUser.role)
    })()
  }, [accessToken])

  useEffect(() => {
    if (loading) return
    if (!tradingDates.includes(reportDate)) {
      setReconciliationReport(null)
      setReportError('No trading record exists for this date.')
      return
    }
    void loadReconciliationReport(reportDate)
  }, [loadReconciliationReport, reportDate, tradingDates, loading])

  useEffect(() => {
    if (!managerAccounts.length) {
      setSelectedManagerAccountCode('')
      return
    }
    if (!selectedManagerAccountCode || !managerAccounts.some((account) => account.code === selectedManagerAccountCode)) {
      setSelectedManagerAccountCode(managerAccounts[0].code)
      return
    }
    if (loading) return
    if (!tradingDates.includes(reportDate)) {
      setManagerReconciliation(null)
      setManagerReportError('No trading record exists for this date.')
      return
    }
    void loadManagerReconciliation(selectedManagerAccountCode, reportDate)
  }, [managerAccounts, selectedManagerAccountCode, loadManagerReconciliation, reportDate, tradingDates, loading])

  useEffect(() => {
    if (!clients.length) {
      setSelectedClientId('')
      return
    }
    if (!clients.some((client) => client.id === selectedClientId)) setSelectedClientId(clients[0].id)
  }, [clients, selectedClientId])

  useEffect(() => {
    void loadClientDetail(selectedClientId)
  }, [loadClientDetail, selectedClientId])

  useEffect(() => {
    const client = clients.find((item) => item.id === editingClientId)
    if (!client) return
    setClientForm({ client_code: client.client_code, name: client.name, opening_capital: client.opening_capital, join_date: client.join_date, contact: client.contact ?? '', notes: client.notes ?? '', status: client.status, fee_type: client.fee_type, fee_value: client.fee_value, fee_basis: client.fee_basis ?? '', fee_start_date: client.fee_start_date ?? '' })
  }, [clients, editingClientId])

  const cards = dashboard
    ? [
        { label: 'Current capital', value: money(dashboard.total_current_capital), note: 'Latest client ledger balances' },
        { label: 'Month to date', value: money(dashboard.current_month_pnl), note: 'Net trading P&L' },
        { label: 'Total net P&L', value: money(dashboard.total_net_pnl), note: `${money(dashboard.today_pnl)} today` },
        { label: 'Active clients', value: dashboard.active_clients.toString(), note: `${money(dashboard.total_fees)} fees booked` },
      ]
    : []

  async function previewWorkbook(file: File) {
    setImporting(true)
    setImportError('')
    setWorkbookPreview(null)
    setSelectedWorkbook(file)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`${API_URL}/import/excel`, { method: 'POST', body: formData })
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Workbook preview failed')
      }
      setWorkbookPreview(await response.json() as WorkbookPreview)
    } catch (caught) {
      setImportError(caught instanceof Error ? caught.message : 'Workbook preview failed')
    } finally {
      setImporting(false)
    }
  }

  async function signIn() {
    setSigningIn(true)
    setAuthError('')
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!response.ok) throw new Error('Invalid username or password')
      const result = await response.json() as LoginResponse
      localStorage.setItem('trading-fund-access-token', result.access_token)
      localStorage.setItem('trading-fund-user-role', result.role)
      setAccessToken(result.access_token)
      setUserRole(result.role)
      setPassword('')
    } catch (caught) {
      setAuthError(caught instanceof Error ? caught.message : 'Sign-in failed')
    } finally {
      setSigningIn(false)
    }
  }

  async function commitWorkbook() {
    if (!selectedWorkbook || !accessToken) return
    setCommitting(true)
    setImportError('')
    setCommitMessage('')
    try {
      const formData = new FormData()
      formData.append('file', selectedWorkbook)
      const response = await fetch(`${API_URL}/import/excel/commit`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      })
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          localStorage.removeItem('trading-fund-access-token')
          localStorage.removeItem('trading-fund-user-role')
          setAccessToken('')
          setUserRole('')
        }
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Workbook commit failed')
      }
      const result = await response.json() as { imported: Record<string, number> }
      setCommitMessage(`Imported ${Object.values(result.imported).reduce((total, count) => total + count, 0)} records successfully.`)
      await loadData()
    } catch (caught) {
      setImportError(caught instanceof Error ? caught.message : 'Workbook commit failed')
    } finally {
      setCommitting(false)
    }
  }

  async function saveTradingEntry() {
    if (userRole !== 'ADMIN') {
      setTradingError('Administrator access is required to save daily trading results.')
      return
    }
    if (!tradingForm.trading_date || !tradingForm.gross_trading_pnl || !tradingForm.transaction_charges) {
      setTradingError('Please complete the date, gross P&L, and charges.')
      return
    }

    setSavingTrading(true)
    setTradingError('')
    try {
      const response = await fetch(`${API_URL}/trading`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
          trading_date: tradingForm.trading_date,
          gross_trading_pnl: Number(tradingForm.gross_trading_pnl),
          transaction_charges: Number(tradingForm.transaction_charges),
          remarks: tradingForm.remarks || null,
        }),
      })

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          localStorage.removeItem('trading-fund-access-token')
          setAccessToken('')
        }
        const detail = await response.json().catch(() => null) as { detail?: string | string[] } | null
        const message = Array.isArray(detail?.detail) ? detail.detail.join(', ') : detail?.detail ?? 'Unable to save trading result.'
        throw new Error(message)
      }

      const allocationResponse = await fetch(`${API_URL}/trading/${tradingForm.trading_date}/allocation`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      })

      if (!allocationResponse.ok) {
        const detail = await allocationResponse.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Allocation could not be calculated.')
      }

      const allocation = await allocationResponse.json() as DailyAllocation
      setDailyAllocation(allocation)
      setTradingForm((current) => ({ ...current, remarks: '' }))
      await loadData()
    } catch (caught) {
      setTradingError(caught instanceof Error ? caught.message : 'Unable to save trading result.')
    } finally {
      setSavingTrading(false)
    }
  }

  async function deleteLatestTradingEntry() {
    const latest = trading[trading.length - 1]
    if (!latest || userRole !== 'ADMIN') return
    if (!confirm(`Delete the daily trading result for ${latest.trading_date}?`)) return
    setSavingTrading(true)
    setTradingError('')
    try {
      const response = await fetch(`${API_URL}/trading/${latest.trading_date}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'Unable to delete the daily trading result.')
      }
      setDailyAllocation(null)
      await loadData()
    } catch (caught) {
      setTradingError(caught instanceof Error ? caught.message : 'Unable to delete the daily trading result.')
    } finally {
      setSavingTrading(false)
    }
  }

  async function saveClient() {
    if (!accessToken) return setAdminError('Sign in before changing client records.')
    if (!clientForm.client_code || !clientForm.name || !clientForm.opening_capital || !clientForm.join_date) return setAdminError('Complete the client code, name, opening capital, and join date.')
    setAdminSaving(true); setAdminError(''); setAdminMessage('')
    try {
      const path = editingClientId ? `/clients/${editingClientId}` : '/clients'
      const response = await fetch(`${API_URL}${path}`, { method: editingClientId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ ...clientForm, opening_capital: Number(clientForm.opening_capital), fee_value: Number(clientForm.fee_value || 0), contact: clientForm.contact || null, notes: clientForm.notes || null, fee_basis: clientForm.fee_basis || null, fee_start_date: clientForm.fee_start_date || null }) })
      const payload = await response.json().catch(() => null) as Client | { detail?: string | string[] } | null
      if (!response.ok) throw new Error(Array.isArray((payload as { detail?: string[] } | null)?.detail) ? (payload as { detail: string[] }).detail.join(', ') : (payload as { detail?: string } | null)?.detail ?? 'Unable to save client')
      const saved = payload as Client
      setEditingClientId(saved.id); setSelectedClientId(saved.id); setAdminMessage(`Client ${editingClientId ? 'updated' : 'created'}.`)
      await loadData(); await loadClientDetail(saved.id)
    } catch (caught) { setAdminError(caught instanceof Error ? caught.message : 'Unable to save client.') } finally { setAdminSaving(false) }
  }

  async function saveStatusPeriod() {
    if (!accessToken) return setAdminError('Sign in before changing client records.')
    if (!statusForm.client_id || !statusForm.from_date || !statusForm.to_date) return setAdminError('Choose a client and complete the status dates.')
    setAdminSaving(true); setAdminError(''); setAdminMessage('')
    try {
      const response = await fetch(`${API_URL}/status-history`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ ...statusForm, remarks: statusForm.remarks || null }) })
      const detail = await response.json().catch(() => null) as { detail?: string | string[] } | null
      if (!response.ok) throw new Error(Array.isArray(detail?.detail) ? detail.detail.join(', ') : detail?.detail ?? 'Unable to save status period')
      setSelectedClientId(statusForm.client_id); setAdminMessage('Status period recorded.'); await loadClientDetail(statusForm.client_id)
    } catch (caught) { setAdminError(caught instanceof Error ? caught.message : 'Unable to save status period.') } finally { setAdminSaving(false) }
  }

  async function saveMovement() {
    if (!accessToken) return setAdminError('Sign in before changing client records.')
    if (!movementForm.client_id || !movementForm.date || !movementForm.amount) return setAdminError('Choose a client and complete the movement date and amount.')
    setAdminSaving(true); setAdminError(''); setAdminMessage('')
    try {
      const response = await fetch(`${API_URL}/fund-movements`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ ...movementForm, amount: Number(movementForm.amount), remarks: movementForm.remarks || null }) })
      const detail = await response.json().catch(() => null) as { detail?: string | string[] } | null
      if (!response.ok) throw new Error(Array.isArray(detail?.detail) ? detail.detail.join(', ') : detail?.detail ?? 'Unable to record movement')
      setSelectedClientId(movementForm.client_id); setMovementForm((current) => ({ ...current, amount: '', remarks: '' })); setAdminMessage('Fund movement recorded.'); await loadData(); await loadClientDetail(movementForm.client_id)
    } catch (caught) { setAdminError(caught instanceof Error ? caught.message : 'Unable to record movement.') } finally { setAdminSaving(false) }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">TF</div>
        <div>
          <p className="eyebrow">Operations desk</p>
          <h1>Trading Fund</h1>
        </div>
        <nav>
          <a className="nav-item active" href="#overview"><span>◈</span> Overview</a>
          <a className="nav-item" href="#clients"><span>◌</span> Clients</a>
          <a className="nav-item" href="#client-admin"><span>+</span> Client administration</a>
          <a className="nav-item" href="#trading"><span>↗</span> Trading journal</a>
          <a className="nav-item" href="#import"><span>⇧</span> Import workbook</a>
        </nav>
        <div className="sidebar-footer">
          <span className={backendReady ? 'status-dot' : 'status-dot offline'} />
          <span>{backendReady ? 'Backend connected' : 'Backend unavailable'}</span>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">{currentDateLabel}</p>
            <h2>Good morning, manager.</h2>
          </div>
          <button className="date-button" type="button" onClick={() => void loadData(new AbortController().signal)} disabled={loading} aria-label="Refresh dashboard data">
            {loading ? 'Refreshing...' : `Refresh · ${currentYear}`}
            <span>↻</span>
          </button>
        </header>

        {error && <div className="notice">{error}</div>}

        <div className="section-heading" id="overview">
          <div><p className="eyebrow">Portfolio pulse</p><h3>Today at a glance</h3></div>
          <span className="live-label"><span className={backendReady ? 'status-dot' : 'status-dot offline'} /> {backendReady ? 'Live data' : 'Offline data'}</span>
        </div>
        <div className="metric-grid">
          {cards.length ? cards.map((card) => (
            <article className="metric-card" key={card.label}>
              <p>{card.label}</p><strong>{card.value}</strong><span>{card.note}</span>
            </article>
          )) : <div className="loading-card">Loading portfolio data...</div>}
        </div>

        <div className="main-grid">
          <section className="panel chart-panel" id="trading">
            <div className="panel-heading"><div><p className="eyebrow">Trading journal</p><h3>Net P&L trend</h3></div><span className="panel-meta">Last 8 entries</span></div>
            <div className="chart-wrap">
              <Suspense fallback={<div className="empty-state">Loading chart...</div>}><PnlChart trading={trading} /></Suspense>
            </div>
          </section>

          <section className="panel clients-panel" id="clients">
            <div className="panel-heading"><div><p className="eyebrow">Capital register</p><h3>Client book</h3></div><span className="panel-meta">{clients.length} records</span></div>
            <div className="client-list">
              {clients.length ? clients.slice(0, showAllClients ? clients.length : 5).map((client) => <button className={`client-row ${selectedClientId === client.id ? 'selected' : ''}`} type="button" key={client.id} onClick={() => setSelectedClientId(client.id)}><span className="client-initial">{client.name.slice(0, 1)}</span><span className="client-name"><strong>{client.name}</strong><span>{client.client_code} · {client.fee_type}</span></span><span className="client-capital"><strong>{money(client.current_balance ?? client.opening_capital)}</strong><span className="active-status">{client.status}</span></span></button>) : <div className="empty-state">Client records will appear here.</div>}
            </div>
            {clients.length > 5 && <button className="text-button" type="button" onClick={() => setShowAllClients((visible) => !visible)}>{showAllClients ? 'Show fewer clients' : 'View all clients'} <span>{showAllClients ? '↑' : '→'}</span></button>}
          </section>
        </div>

        <section className="panel administration-panel" id="client-admin">
          <div className="panel-heading"><div><p className="eyebrow">Client administration</p><h3>Capital, fees, status, and history</h3></div><span className="panel-meta">Authenticated changes</span></div>
          {userRole === 'ADMIN' && <div className="admin-grid">
            <form className="admin-form" onSubmit={(event) => { event.preventDefault(); void saveClient() }}>
              <div className="form-title"><strong>Client and fee setup</strong><select value={editingClientId} onChange={(event) => { setEditingClientId(event.target.value); if (!event.target.value) setClientForm({ client_code: '', name: '', opening_capital: '', join_date: new Date().toISOString().slice(0, 10), contact: '', notes: '', status: 'ACTIVE', fee_type: 'NONE', fee_value: '0', fee_basis: '', fee_start_date: '' }) }}><option value="">New client</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></div>
              <label>Client code<input value={clientForm.client_code} onChange={(event) => setClientForm((current) => ({ ...current, client_code: event.target.value }))} /></label><label>Name<input value={clientForm.name} onChange={(event) => setClientForm((current) => ({ ...current, name: event.target.value }))} /></label><label>Opening capital<input type="number" min="0" step="0.01" value={clientForm.opening_capital} onChange={(event) => setClientForm((current) => ({ ...current, opening_capital: event.target.value }))} /></label><label>Join date<input type="date" value={clientForm.join_date} onChange={(event) => setClientForm((current) => ({ ...current, join_date: event.target.value }))} /></label><label>Status<select value={clientForm.status} onChange={(event) => setClientForm((current) => ({ ...current, status: event.target.value }))}><option>ACTIVE</option><option>INACTIVE</option></select></label><label>Fee type<select value={clientForm.fee_type} onChange={(event) => setClientForm((current) => ({ ...current, fee_type: event.target.value }))}><option>NONE</option><option>PERCENTAGE</option><option>FIXED</option></select></label><label>Fee value<input type="number" min="0" step="0.01" value={clientForm.fee_value} onChange={(event) => setClientForm((current) => ({ ...current, fee_value: event.target.value }))} /></label><label>Fee basis<input value={clientForm.fee_basis} onChange={(event) => setClientForm((current) => ({ ...current, fee_basis: event.target.value }))} placeholder="Optional basis" /></label><label>Fee start<input type="date" value={clientForm.fee_start_date} onChange={(event) => setClientForm((current) => ({ ...current, fee_start_date: event.target.value }))} /></label><label className="form-wide">Contact<input value={clientForm.contact} onChange={(event) => setClientForm((current) => ({ ...current, contact: event.target.value }))} /></label><button className="date-button" disabled={adminSaving}>{adminSaving ? 'Saving...' : editingClientId ? 'Update client' : 'Add client'}</button>
            </form>
            <form className="admin-form" onSubmit={(event) => { event.preventDefault(); void saveStatusPeriod() }}>
              <div className="form-title"><strong>Active period</strong></div><label className="form-wide">Client<select value={statusForm.client_id} onChange={(event) => setStatusForm((current) => ({ ...current, client_id: event.target.value }))}><option value="">Choose client</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label><label>Status<select value={statusForm.status} onChange={(event) => setStatusForm((current) => ({ ...current, status: event.target.value }))}><option>ACTIVE</option><option>INACTIVE</option></select></label><label>From<input type="date" value={statusForm.from_date} onChange={(event) => setStatusForm((current) => ({ ...current, from_date: event.target.value }))} /></label><label>To<input type="date" value={statusForm.to_date} onChange={(event) => setStatusForm((current) => ({ ...current, to_date: event.target.value }))} /></label><label className="form-wide">Remarks<input value={statusForm.remarks} onChange={(event) => setStatusForm((current) => ({ ...current, remarks: event.target.value }))} /></label><button className="date-button" disabled={adminSaving}>Record period</button>
            </form>
            <form className="admin-form" onSubmit={(event) => { event.preventDefault(); void saveMovement() }}>
              <div className="form-title"><strong>Deposit or withdrawal</strong></div><label className="form-wide">Client<select value={movementForm.client_id} onChange={(event) => setMovementForm((current) => ({ ...current, client_id: event.target.value }))}><option value="">Choose client</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label><label>Date<input type="date" value={movementForm.date} onChange={(event) => setMovementForm((current) => ({ ...current, date: event.target.value }))} /></label><label>Type<select value={movementForm.movement_type} onChange={(event) => setMovementForm((current) => ({ ...current, movement_type: event.target.value }))}><option>DEPOSIT</option><option>WITHDRAWAL</option></select></label><label>Amount<input type="number" min="0.01" step="0.01" value={movementForm.amount} onChange={(event) => setMovementForm((current) => ({ ...current, amount: event.target.value }))} /></label><label className="form-wide">Remarks<input value={movementForm.remarks} onChange={(event) => setMovementForm((current) => ({ ...current, remarks: event.target.value }))} /></label><button className="date-button" disabled={adminSaving}>Record movement</button>
            </form>
          </div>}
          {userRole === 'ADMIN' && <>{adminError && <p className="import-error">{adminError}</p>}{adminMessage && <p className="commit-success">{adminMessage}</p>}</>}
          {clientDetail && <div className="client-detail"><div className="panel-heading"><div><p className="eyebrow">Client ledger</p><h3>{clientDetail.client.name}</h3></div><span className="panel-meta">{clientDetail.summary.current_status}</span></div><div className="summary-grid"><div className="summary-item"><span>Current capital</span><strong>{money(clientDetail.summary.current_capital)}</strong></div><div className="summary-item"><span>Net P&L</span><strong>{money(clientDetail.summary.net_pnl)}</strong></div><div className="summary-item"><span>Fees</span><strong>{money(clientDetail.summary.total_fees)}</strong></div><div className="summary-item"><span>Withdrawn</span><strong>{money(clientDetail.summary.total_withdrawn)}</strong></div></div><div className="allocation-table-wrap"><table className="allocation-table"><thead><tr><th>Date</th><th>Movement</th><th>Allocated P&L</th><th>Fee</th><th>Net P&L</th><th>Closing balance</th><th>Status</th></tr></thead><tbody>{clientDetail.ledger.length ? clientDetail.ledger.map((entry) => <tr key={entry.trading_date}><td>{entry.trading_date}</td><td>{money(entry.fund_movement)}</td><td>{money(entry.allocated_pnl)}</td><td>{money(entry.fee_debited)}</td><td>{money(entry.net_client_pnl)}</td><td>{money(entry.closing_balance)}</td><td>{entry.status_on_date}</td></tr>) : <tr><td colSpan={7}>No ledger entries yet.</td></tr>}</tbody></table></div>{auditEntries.length > 0 && <div className="audit-list"><strong>Audit trail</strong>{auditEntries.map((entry) => <span key={entry.id}>{entry.action} {entry.entity_type.replace('_', ' ').toLowerCase()} · {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : ''}</span>)}</div>}</div>}
        </section>

        <section className="panel manager-panel">
          <div className="panel-heading"><div><p className="eyebrow">Manager treasury</p><h3>Manager accounts</h3></div><span className="panel-meta">Fee reconciliation</span></div>
          <div className="manager-grid">
            {managerAccounts.length ? managerAccounts.map((account) => (
              <article className="manager-card" key={account.id}>
                <div className="manager-card-header">
                  <div>
                    <p className="manager-code">{account.code}</p>
                    <h4>{account.name}</h4>
                  </div>
                  <span className="manager-pill">Live</span>
                </div>
                <div className="manager-metrics">
                  <div><span>Opening capital</span><strong>{money(account.opening_capital)}</strong></div>
                  <div><span>Fees received</span><strong>{money(account.fees_received)}</strong></div>
                  <div><span>Current balance</span><strong>{money(account.current_balance)}</strong></div>
                </div>
              </article>
            )) : <div className="empty-state">Manager accounts will be listed here.</div>}
          </div>

          <div className="manager-drilldown">
            <div className="report-toolbar">
              <label>
                <span>Manager account</span>
                <select value={selectedManagerAccountCode} onChange={(event) => setSelectedManagerAccountCode(event.target.value)}>
                  {managerAccounts.map((account) => (
                    <option key={account.id} value={account.code}>{account.name}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>As of date</span>
                <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
              </label>
              <button className="date-button" type="button" onClick={() => void loadManagerReconciliation(selectedManagerAccountCode, reportDate)} disabled={managerReportLoading || !selectedManagerAccountCode}>
                {managerReportLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
            {managerReportError && <p className="import-error">{managerReportError}</p>}
            {managerReconciliation && (
              <div className="summary-grid report-grid">
                <div className="summary-item"><span>Opening capital</span><strong>{money(managerReconciliation.opening_capital)}</strong></div>
                <div className="summary-item"><span>Fees received</span><strong>{money(managerReconciliation.fees_received)}</strong></div>
                <div className="summary-item"><span>Expected client fees</span><strong>{money(managerReconciliation.expected_client_fees)}</strong></div>
                <div className="summary-item"><span>Fee transfer delta</span><strong>{money(managerReconciliation.fee_transfer_delta)}</strong></div>
                <div className="summary-item"><span>Current balance</span><strong>{money(managerReconciliation.current_balance)}</strong></div>
                <div className="summary-item highlight"><span>Reconciliation</span><strong>{managerReconciliation.fees_reconciled ? 'Reconciled' : 'Open'}</strong></div>
              </div>
            )}
          </div>
        </section>

        <section className="panel reporting-panel">
          <div className="panel-heading"><div><p className="eyebrow">Reporting</p><h3>Reconciliation view</h3></div><span className="panel-meta">Daily control check</span></div>
          <div className="report-toolbar">
            <label>
              <span>Trading date</span>
              <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
            </label>
            <button className="date-button" type="button" onClick={() => void loadReconciliationReport(reportDate)} disabled={reportLoading}>
              {reportLoading ? 'Loading...' : 'Refresh report'}
            </button>
            <a className="text-button export-link" href={`${API_URL}/reports/daily/export?trading_date=${reportDate}`}>Export CSV</a>
          </div>
          {reportError && <p className="import-error">{reportError}</p>}
          {reconciliationReport && (
            <>
              <div className="summary-grid report-grid">
                <div className="summary-item"><span>Net P&L</span><strong>{money(reconciliationReport.net_pnl)}</strong></div>
                <div className="summary-item"><span>Allocated P&L</span><strong>{money(reconciliationReport.allocated_pnl)}</strong></div>
                <div className="summary-item"><span>Allocation delta</span><strong>{money(reconciliationReport.allocation_delta)}</strong></div>
                <div className="summary-item"><span>Client fees</span><strong>{money(reconciliationReport.total_client_fees)}</strong></div>
                <div className="summary-item"><span>Manager fee credits</span><strong>{money(reconciliationReport.manager_fee_credits)}</strong></div>
                <div className="summary-item"><span>Fee transfer delta</span><strong>{money(reconciliationReport.fee_transfer_delta)}</strong></div>
                <div className="summary-item highlight"><span>Allocation status</span><strong>{reconciliationReport.allocation_reconciled ? 'Reconciled' : 'Open'}</strong></div>
                <div className="summary-item highlight"><span>Fee status</span><strong>{reconciliationReport.fees_reconciled ? 'Reconciled' : 'Open'}</strong></div>
              </div>
            </>
          )}
        </section>

        <section className="panel trading-panel" id="daily-trading">
          <div className="panel-heading"><div><p className="eyebrow">Daily trade</p><h3>Enter trading result</h3></div><span className="panel-meta">Fast daily capture</span></div>
          {userRole === 'ADMIN' && <><div className="trading-form">
            <label>
              <span>Date</span>
              <input type="date" value={tradingForm.trading_date} onChange={(event) => setTradingForm((current) => ({ ...current, trading_date: event.target.value }))} />
            </label>
            <label>
              <span>Gross Trading P&L</span>
              <input type="number" step="0.01" value={tradingForm.gross_trading_pnl} onChange={(event) => setTradingForm((current) => ({ ...current, gross_trading_pnl: event.target.value }))} placeholder="0.00" />
            </label>
            <label>
              <span>Transaction Charges</span>
              <input type="number" step="0.01" value={tradingForm.transaction_charges} onChange={(event) => setTradingForm((current) => ({ ...current, transaction_charges: event.target.value }))} placeholder="0.00" />
            </label>
            <label className="full-width">
              <span>Remarks</span>
              <input type="text" value={tradingForm.remarks} onChange={(event) => setTradingForm((current) => ({ ...current, remarks: event.target.value }))} placeholder="Daily market note" />
            </label>
          </div>
          <div className="commit-row trading-row">
            <span>{tradingForm.gross_trading_pnl && tradingForm.transaction_charges ? `Net P&L: ${money((Number(tradingForm.gross_trading_pnl) - Number(tradingForm.transaction_charges)).toFixed(2))}` : 'Net P&L: ₹0.00'}</span>
            <div className="trading-actions"><button className="date-button" type="button" onClick={() => void saveTradingEntry()} disabled={savingTrading}>{savingTrading ? 'Saving...' : 'Save Trading Result'}</button>{trading.length > 0 && <button className="text-button danger-button" type="button" onClick={() => void deleteLatestTradingEntry()} disabled={savingTrading}>Delete latest ({trading[trading.length - 1]?.trading_date})</button>}</div>
          </div>
          </>}
          {tradingError && <p className="import-error">{tradingError}</p>}
        </section>

        {dailyAllocation && (
          <section className="panel allocation-panel">
            <div className="panel-heading"><div><p className="eyebrow">Allocation check</p><h3>Daily reconciliation</h3></div><span className="panel-meta">{dailyAllocation.trading_date}</span></div>
            <div className="summary-grid">
              <div className="summary-item"><span>Active capital</span><strong>{money(dailyAllocation.active_capital)}</strong></div>
              <div className="summary-item"><span>Active clients</span><strong>{dailyAllocation.active_clients}</strong></div>
              <div className="summary-item"><span>Net trading P&L</span><strong>{money(dailyAllocation.net_pnl)}</strong></div>
              <div className="summary-item"><span>Allocated P&L</span><strong>{money(dailyAllocation.allocated_pnl)}</strong></div>
              <div className="summary-item"><span>Total fees</span><strong>{money(dailyAllocation.total_fees)}</strong></div>
              <div className="summary-item"><span>Manager fee</span><strong>{money(dailyAllocation.manager_fee)}</strong></div>
              <div className="summary-item highlight"><span>Allocation check</span><strong>{money(dailyAllocation.allocation_difference)}</strong></div>
            </div>
            <div className="allocation-table-wrap">
              <table className="allocation-table">
                <thead>
                  <tr>
                    <th>Client</th>
                    <th>Capital</th>
                    <th>Share %</th>
                    <th>Allocated P&L</th>
                    <th>Fee</th>
                    <th>Net P&L</th>
                    <th>Closing Capital</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyAllocation.entries.map((entry) => (
                    <tr key={entry.client_id}>
                      <td>{entry.client_name}</td>
                      <td>{money(entry.capital)}</td>
                      <td>{money(entry.share_percent)}</td>
                      <td>{money(entry.allocated_pnl)}</td>
                      <td>{money(entry.fee)}</td>
                      <td>{money(entry.net_pnl)}</td>
                      <td>{money(entry.closing_balance)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="panel import-panel" id="import">
          <div className="panel-heading"><div><p className="eyebrow">Workbook intake</p><h3>Preview an Excel file</h3></div><span className="panel-meta">No database changes</span></div>
          <div className="import-controls">
            <label className="file-picker">
              <span>{importing ? 'Reading workbook...' : 'Choose .xlsx workbook'}</span>
              <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={importing} onChange={(event) => { const file = event.target.files?.[0]; if (file) void previewWorkbook(file) }} />
            </label>
            {importError && <p className="import-error">{importError}</p>}
          </div>
          {!accessToken && <div className="auth-controls"><input aria-label="Username" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} /><input aria-label="Password" type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} /><button className="text-button" type="button" onClick={() => void signIn()} disabled={signingIn || !username || !password}>{signingIn ? 'Signing in...' : 'Sign in to commit'}</button>{authError && <p className="import-error">{authError}</p>}</div>}
          {workbookPreview && <div className="preview-table"><strong>{workbookPreview.filename}</strong>{workbookPreview.sheets.map((sheet) => { const mapping = workbookPreview.mappings.find((item) => item.sheet === sheet.name); return <div className="preview-row" key={sheet.name}><span>{sheet.name}</span><span>{sheet.rows} rows · {sheet.columns} columns</span><span className={mapping?.recognized ? 'active-status' : 'import-error'}>{mapping?.recognized ? `${mapping.data_rows} data rows mapped` : 'Not recognized'}</span></div> })}</div>}
          {workbookPreview && <div className="commit-row"><span>{accessToken ? 'Authenticated for commit' : 'Sign in to enable commit'}</span><button className="date-button" type="button" onClick={() => void commitWorkbook()} disabled={committing || !accessToken || !selectedWorkbook}>{committing ? 'Committing...' : 'Commit workbook'}</button></div>}
          {commitMessage && <p className="commit-success">{commitMessage}</p>}
        </section>
      </section>
    </main>
  )
}
