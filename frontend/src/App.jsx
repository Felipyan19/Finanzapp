import { useEffect, useMemo, useState } from 'react'
import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import {
  cancelGoal,
  completeFixedTransaction,
  contributeToGoal,
  createAccount,
  createFixedTransaction,
  createGoal,
  createTransfer,
  createTransaction,
  deactivateAccount,
  deleteFixedTransaction,
  fetchAccounts,
  fetchBillOccurrences,
  fetchBills,
  fetchCategories,
  fetchFixedTransactions,
  fetchGoals,
  fetchRecurringTransactions,
  fetchTransactions,
  fetchTransactionSummary,
  omitFixedTransaction,
  payBillOccurrence,
  updateAccount,
  updateBillOccurrence,
  updateFixedTransaction,
} from './lib/api'

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <div className="loading-screen"><span className="material-symbols-outlined spin">progress_activity</span></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

const fallbackSavingsGoals = [
  {
    id: 'new-car',
    type: 'bar',
    backend: false,
    title: 'Auto nuevo',
    icon: 'directions_car',
    current: 18000,
    target: 25000,
    percent: 72,
    eta: 'Est. oct 2026',
    status: 'active',
  },
  {
    id: 'emergency',
    type: 'ring',
    backend: false,
    title: 'Fondo de emergencia',
    subtitle: 'Colchón para 6 meses',
    current: 13500,
    target: 15000,
    percent: 90,
    status: 'active',
  },
  {
    id: 'vacation',
    type: 'image',
    backend: false,
    title: 'Vacaciones soñadas',
    icon: 'beach_access',
    current: 2000,
    target: 5000,
    percent: 40,
    eta: 'Est. jun 2026',
    status: 'active',
    image:
      'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80',
  },
]

function App() {
  const { user, isAuthenticated, logout } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const userId = user?.id || null
  const [accounts, setAccounts] = useState([])
  const [transactions, setTransactions] = useState([])
  const [categories, setCategories] = useState([])
  const [bills, setBills] = useState([])
  const [billOccurrences, setBillOccurrences] = useState([])
  const [goals, setGoals] = useState([])
  const [recurringTransactions, setRecurringTransactions] = useState([])
  const [fixedTransactions, setFixedTransactions] = useState([])
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    if (!isAuthenticated) return
    let mounted = true

    async function loadData() {
      try {
        const today = new Date()
        const periodStart = new Date(today.getFullYear(), today.getMonth(), 1)
        const summaryEndDate = today.toISOString().slice(0, 10)
        const startDate = periodStart.toISOString().slice(0, 10)
        const endOfNextMonth = new Date(today.getFullYear(), today.getMonth() + 2, 0)
        const fixedEndDate = endOfNextMonth.toISOString().slice(0, 10)
        const accountsPromise = fetchAccounts({ is_active: true }).then(async (activeAccounts) => {
          if ((activeAccounts || []).length > 0) {
            return activeAccounts
          }
          // Fallback: keep selectors usable even if active flag data is inconsistent.
          return fetchAccounts()
        })

        const [
          accountsData,
          transactionsData,
          categoriesData,
          billsData,
          occurrencesData,
          recurringData,
          fixedData,
          goalsData,
          summaryData,
        ] =
          await Promise.all([
          accountsPromise,
          fetchTransactions(300),
          fetchCategories(),
          fetchBills(),
          fetchBillOccurrences(startDate, fixedEndDate),
          fetchRecurringTransactions().catch(() => []),
          fetchFixedTransactions().catch(() => []),
          fetchGoals(),
          fetchTransactionSummary(startDate, summaryEndDate),
        ])

        if (!mounted) {
          return
        }

        setAccounts(accountsData || [])
        setTransactions(transactionsData || [])
        setCategories(categoriesData || [])
        setBills(billsData || [])
        setBillOccurrences(occurrencesData || [])
        setRecurringTransactions(recurringData || [])
        setFixedTransactions(fixedData || [])
        setGoals(goalsData || [])
        setSummary(summaryData || null)
      } catch (err) {
        if (mounted) {
          setError('No se pudo cargar la API. Mostrando datos de ejemplo.')
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }

    loadData()
    return () => {
      mounted = false
    }
  }, [isAuthenticated])

  const accountsMetrics = useMemo(() => {
    const balances = accounts.map((acc) => Number(acc.current_balance || 0))
    const netWorth = balances.reduce((sum, value) => sum + value, 0)
    const totalAssets = balances.filter((value) => value >= 0).reduce((sum, value) => sum + value, 0)
    const totalLiabilities = balances.filter((value) => value < 0).reduce((sum, value) => sum + Math.abs(value), 0)
    return { netWorth, totalAssets, totalLiabilities }
  }, [accounts])

  const journalGroups = useMemo(() => groupTransactionsByDate(transactions), [transactions])

  const savingsGoals = useMemo(() => {
    if (!goals.length) {
      return fallbackSavingsGoals
    }

    return goals.map((goal, index) => {
      const current = Number(goal.current_amount || 0)
      const target = Number(goal.target_amount || 0)
      const percent = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0
      const variant = index % 3

      if (variant === 1) {
        return {
          id: goal.id,
          type: 'ring',
          backend: true,
          title: goal.name,
          subtitle: goal.status,
          current,
          target,
          percent,
          status: goal.status,
        }
      }

      if (variant === 2) {
        return {
          id: goal.id,
          type: 'image',
          backend: true,
          title: goal.name,
          icon: 'savings',
          current,
          target,
          percent,
          eta: goal.target_date ? `Meta ${formatShortDate(goal.target_date)}` : 'Sin fecha objetivo',
          status: goal.status,
          image:
            'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
        }
      }

      return {
        id: goal.id,
        type: 'bar',
        backend: true,
        title: goal.name,
        icon: 'savings',
        current,
        target,
        percent,
        eta: goal.target_date ? `Meta ${formatShortDate(goal.target_date)}` : 'Sin fecha objetivo',
        status: goal.status,
      }
    })
  }, [goals])

  async function handleCreateTransaction(payload) {
    if (!userId) {
      throw new Error('No hay usuario activo para crear la transacción.')
    }

    let createdTransactions = []
    if (payload.transaction_type === 'transfer') {
      const transferResult = await createTransfer({
        user_id: userId,
        from_account_id: payload.account_id,
        to_account_id: payload.counterparty_account_id,
        amount: payload.amount,
        transaction_date: payload.transaction_date,
        description: payload.description,
      })
      createdTransactions = [transferResult.source_transaction, transferResult.destination_transaction]
    } else {
      const created = await createTransaction({
        user_id: userId,
        source: 'manual',
        ...payload,
      })
      createdTransactions = [created]
    }

    setTransactions((prev) => [...createdTransactions, ...prev])

    const today = new Date()
    const periodStart = new Date(today.getFullYear(), today.getMonth(), 1)
    const startDate = periodStart.toISOString().slice(0, 10)
    const endDate = today.toISOString().slice(0, 10)

    try {
      const summaryData = await fetchTransactionSummary(startDate, endDate)
      setSummary(summaryData || null)
    } catch (_err) {
      // El resumen no es crítico para crear la transacción.
    }

    return createdTransactions[0]
  }

  async function handlePayFixedExpense({ occurrenceId, billId, amount, accountId, paidDate, description }) {
    if (!userId) {
      throw new Error('No hay usuario activo para registrar el pago.')
    }

    const bill = bills.find((item) => item.id === billId)
    const paymentDescription = description || (bill ? `Pago gasto fijo: ${bill.name}` : 'Pago gasto fijo')

    const transaction = await createTransaction({
      user_id: userId,
      transaction_type: 'expense',
      amount: Number(amount),
      currency: 'COP',
      account_id: accountId,
      category_id: bill?.category_id || null,
      transaction_date: paidDate,
      description: paymentDescription,
      status: 'completed',
      source: 'manual',
    })

    await payBillOccurrence(occurrenceId, {
      transaction_id: transaction.id,
      paid_amount: Number(amount),
      paid_date: paidDate,
    })

    setTransactions((prev) => [transaction, ...prev])

    const refreshedOccurrences = billOccurrences.map((occurrence) =>
      occurrence.id === occurrenceId
        ? {
            ...occurrence,
            status: 'paid',
            paid_date: paidDate,
            paid_amount: amount,
            transaction_id: transaction.id,
          }
        : occurrence,
    )
    setBillOccurrences(refreshedOccurrences)

    const today = new Date()
    const periodStart = new Date(today.getFullYear(), today.getMonth(), 1)
    const startDate = periodStart.toISOString().slice(0, 10)
    const endDate = today.toISOString().slice(0, 10)

    try {
      const [summaryData, accountsData] = await Promise.all([
        fetchTransactionSummary(startDate, endDate),
        fetchAccounts(),
      ])
      setSummary(summaryData || null)
      setAccounts(accountsData || [])
    } catch (_err) {
      // Si falla el refresh, mantenemos el estado local actualizado.
    }
  }

  async function handleOmitFixedExpense({ occurrenceId }) {
    if (!userId) {
      throw new Error('No hay usuario activo para actualizar el gasto fijo.')
    }
    const updated = await updateBillOccurrence(occurrenceId, { status: 'cancelled' })
    setBillOccurrences((prev) => prev.map((item) => (item.id === occurrenceId ? updated : item)))
    return updated
  }

  async function handleCreateFixedTransaction(payload) {
    if (!userId) throw new Error('No hay usuario activo.')
    const created = await createFixedTransaction({ user_id: userId, ...payload })
    setFixedTransactions((prev) => [...prev, created])
    return created
  }

  async function handleUpdateFixedTransaction(fixedTxId, payload) {
    if (!userId) throw new Error('No hay usuario activo.')
    const updated = await updateFixedTransaction(fixedTxId, payload)
    setFixedTransactions((prev) => prev.map((item) => (item.id === fixedTxId ? updated : item)))
    return updated
  }

  async function handleDeleteFixedTransaction(fixedTxId) {
    if (!userId) throw new Error('No hay usuario activo.')
    await deleteFixedTransaction(fixedTxId)
    setFixedTransactions((prev) => prev.filter((item) => item.id !== fixedTxId))
  }

  async function handleCompleteFixedTransaction(fixedTxId, payload) {
    if (!userId) throw new Error('No hay usuario activo.')
    const completed = await completeFixedTransaction(fixedTxId, payload)
    setFixedTransactions((prev) => prev.map((item) => (item.id === fixedTxId ? completed : item)))
    const refreshedTransactions = await fetchTransactions(300)
    const refreshedAccounts = await fetchAccounts()
    setTransactions(refreshedTransactions || [])
    setAccounts(refreshedAccounts || [])
    return completed
  }

  async function handleOmitFixedTransaction(fixedTxId) {
    if (!userId) throw new Error('No hay usuario activo.')
    const omitted = await omitFixedTransaction(fixedTxId)
    setFixedTransactions((prev) => prev.map((item) => (item.id === fixedTxId ? omitted : item)))
    return omitted
  }

  async function handleCreateAccount(payload) {
    if (!userId) throw new Error('No hay usuario activo.')
    const created = await createAccount({ user_id: userId, ...payload })
    setAccounts((prev) => [...prev, created])
    return created
  }

  async function handleUpdateAccount(accountId, payload) {
    const updated = await updateAccount(accountId, payload)
    setAccounts((prev) => prev.map((item) => (item.id === accountId ? updated : item)))
    return updated
  }

  async function handleDeactivateAccount(accountId) {
    await deactivateAccount(accountId)
    setAccounts((prev) => prev.filter((item) => item.id !== accountId))
  }

  async function handleCreateGoal(payload) {
    if (!userId) throw new Error('No hay usuario activo.')
    const created = await createGoal({
      user_id: userId,
      ...payload,
    })
    setGoals((prev) => [created, ...prev])
    return created
  }

  async function handleContributeGoal(goalId, amount) {
    if (!userId) throw new Error('No hay usuario activo.')
    const updated = await contributeToGoal(goalId, amount)
    setGoals((prev) => prev.map((item) => (item.id === goalId ? updated : item)))
    return updated
  }

  async function handleCancelGoal(goalId) {
    if (!userId) throw new Error('No hay usuario activo.')
    await cancelGoal(goalId)
    setGoals((prev) => prev.map((item) => (item.id === goalId ? { ...item, status: 'cancelled' } : item)))
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<ProtectedRoute><Navigate to="/panel" replace /></ProtectedRoute>} />
      <Route
        path="/panel"
        element={
          <ProtectedRoute>
          <PanelScreen
            isLoading={isLoading}
            error={error}
            userId={userId}
            metrics={accountsMetrics}
            summary={summary}
            transactions={transactions}
          />
          </ProtectedRoute>
        }
      />
      <Route
        path="/accounts"
        element={
          <ProtectedRoute>
          <AccountsScreen
            isLoading={isLoading}
            error={error}
            userId={userId}
            accounts={accounts}
            metrics={accountsMetrics}
            summary={summary}
            transactions={transactions}
            onCreateAccount={handleCreateAccount}
            onUpdateAccount={handleUpdateAccount}
            onDeactivateAccount={handleDeactivateAccount}
          />
          </ProtectedRoute>
        }
      />
      <Route
        path="/journal"
        element={
          <ProtectedRoute>
          <JournalScreen
            isLoading={isLoading}
            error={error}
            groups={journalGroups}
            transactions={transactions}
            userId={userId}
            accounts={accounts}
            categories={categories}
            fixedTransactions={fixedTransactions}
            onCreateTransaction={handleCreateTransaction}
            onCreateFixedTransaction={handleCreateFixedTransaction}
            onUpdateFixedTransaction={handleUpdateFixedTransaction}
            onDeleteFixedTransaction={handleDeleteFixedTransaction}
            onCompleteFixedTransaction={handleCompleteFixedTransaction}
            onOmitFixedTransaction={handleOmitFixedTransaction}
          />
          </ProtectedRoute>
        }
      />
      <Route
        path="/budgets"
        element={
          <ProtectedRoute>
          <BudgetsScreen
            isLoading={isLoading}
            error={error}
            userId={userId}
            transactions={transactions}
            categories={categories}
          />
          </ProtectedRoute>
        }
      />
      <Route
        path="/savings"
        element={
          <ProtectedRoute>
          <SavingsScreen
            isLoading={isLoading}
            error={error}
            goals={savingsGoals}
            summary={summary}
            userId={userId}
            onCreateGoal={handleCreateGoal}
            onContributeGoal={handleContributeGoal}
            onCancelGoal={handleCancelGoal}
          />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

function TopBar({ title, brand }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="avatar-wrap">
          <img
            src="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=200&q=80"
            alt="Perfil"
          />
        </div>
        <h1>{brand ? 'FinanzApp' : title}</h1>
      </div>
      <div className="topbar-actions">
        {title === 'Diario' && (
          <button type="button" className="icon-btn" aria-label="Buscar">
            <span className="material-symbols-outlined">search</span>
          </button>
        )}
        <button type="button" className="icon-btn" aria-label="Notificaciones">
          <span className="material-symbols-outlined">notifications</span>
        </button>
      </div>
    </header>
  )
}

function BottomNav() {
  const items = [
    { label: 'Panel', icon: 'dashboard', to: '/panel' },
    { label: 'Cuentas', icon: 'account_balance', to: '/accounts' },
    { label: 'Movimientos', icon: 'swap_horiz', to: '/journal' },
    { label: 'Presupuestos', icon: 'payments', to: '/budgets' },
    { label: 'Ahorros', icon: 'savings', to: '/savings' },
  ]

  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <NavLink
          key={`${item.label}-${item.to}`}
          to={item.to}
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <span className="material-symbols-outlined">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

function Screen({ title, brand = false, children, error, userId }) {
  return (
    <div className="screen-shell">
      <TopBar title={title} brand={brand} />
      <main className="screen-content">
        {error && <p className="api-warning">{error}</p>}
        {children}
      </main>
      <BottomNav />
    </div>
  )
}

function SavingsScreen({ goals, summary, isLoading, error, userId, onCreateGoal, onContributeGoal, onCancelGoal }) {
  const totalSaved = goals.reduce((sum, goal) => sum + Number(goal.current || 0), 0)
  const monthlyContribution = Number(summary?.net_balance || 0)
  const [actionError, setActionError] = useState('')
  const [createModal, setCreateModal] = useState({
    open: false,
    isSubmitting: false,
    draft: {
      name: '',
      targetAmount: '',
      targetDate: '',
      priority: '1',
    },
  })
  const [contributeModal, setContributeModal] = useState({
    open: false,
    goalId: '',
    goalTitle: '',
    isSubmitting: false,
    amount: '',
  })

  function openCreateModal() {
    setActionError('')
    setCreateModal((prev) => ({ ...prev, open: true }))
  }

  function closeCreateModal() {
    if (createModal.isSubmitting) return
    setCreateModal((prev) => ({ ...prev, open: false }))
  }

  function updateCreateDraft(field, value) {
    setCreateModal((prev) => ({
      ...prev,
      draft: {
        ...prev.draft,
        [field]: value,
      },
    }))
  }

  async function submitCreateGoal(event) {
    event.preventDefault()
    setActionError('')
    const targetAmount = Number(createModal.draft.targetAmount)
    if (!createModal.draft.name.trim()) {
      setActionError('El nombre de la meta es obligatorio.')
      return
    }
    if (!targetAmount || targetAmount <= 0) {
      setActionError('El monto objetivo debe ser mayor a cero.')
      return
    }
    try {
      setCreateModal((prev) => ({ ...prev, isSubmitting: true }))
      await onCreateGoal({
        name: createModal.draft.name.trim(),
        target_amount: targetAmount,
        target_date: createModal.draft.targetDate || null,
        priority: Number(createModal.draft.priority || 1),
      })
      setCreateModal({
        open: false,
        isSubmitting: false,
        draft: {
          name: '',
          targetAmount: '',
          targetDate: '',
          priority: '1',
        },
      })
    } catch (_err) {
      setActionError('No se pudo crear la meta.')
      setCreateModal((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  function openContributeModal(goal) {
    if (!goal.backend || goal.status === 'cancelled') return
    setActionError('')
    setContributeModal({
      open: true,
      goalId: goal.id,
      goalTitle: goal.title,
      isSubmitting: false,
      amount: '',
    })
  }

  function closeContributeModal() {
    if (contributeModal.isSubmitting) return
    setContributeModal((prev) => ({ ...prev, open: false }))
  }

  async function submitContribution(event) {
    event.preventDefault()
    setActionError('')
    const amount = Number(contributeModal.amount)
    if (!amount || amount <= 0) {
      setActionError('El aporte debe ser mayor a cero.')
      return
    }
    try {
      setContributeModal((prev) => ({ ...prev, isSubmitting: true }))
      await onContributeGoal(contributeModal.goalId, amount)
      setContributeModal((prev) => ({ ...prev, open: false, isSubmitting: false }))
    } catch (_err) {
      setActionError('No se pudo registrar el aporte.')
      setContributeModal((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  async function handleCancelGoalClick(goal) {
    if (!goal.backend || goal.status === 'cancelled') return
    if (!window.confirm(`Cancelar la meta "${goal.title}"?`)) {
      return
    }
    try {
      setActionError('')
      await onCancelGoal(goal.id)
    } catch (_err) {
      setActionError('No se pudo cancelar la meta.')
    }
  }

  function renderGoalActions(goal, dark = false) {
    if (!goal.backend) {
      return <small className={`goal-note ${dark ? 'goal-note-dark' : ''}`}>Meta local de ejemplo</small>
    }
    return (
      <div className="goal-actions">
        <button type="button" onClick={() => openContributeModal(goal)} disabled={goal.status === 'cancelled'}>
          Aportar
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => handleCancelGoalClick(goal)}
          disabled={goal.status === 'cancelled'}
        >
          {goal.status === 'cancelled' ? 'Cancelada' : 'Cancelar'}
        </button>
      </div>
    )
  }

  return (
    <Screen title="Ahorros" brand error={error} userId={userId}>
      <section className="section-head">
        <h2>Metas de ahorro</h2>
        <p>Sigue tu avance hacia la libertad financiera.</p>
        {actionError && <p className="api-warning">{actionError}</p>}
      </section>

      <section className="grid-cards">
        {goals.map((goal) => {
          if (goal.type === 'ring') {
            const radius = 42
            const circumference = 2 * Math.PI * radius
            const dashOffset = circumference - (goal.percent / 100) * circumference
            return (
              <article key={goal.id} className="card card-ring">
                <div className="ring-header">
                  <div className="progress-ring-wrap">
                    <svg viewBox="0 0 100 100" className="progress-ring">
                      <circle cx="50" cy="50" r={radius} className="ring-base" />
                      <circle
                        cx="50"
                        cy="50"
                        r={radius}
                        className="ring-progress"
                        style={{ strokeDasharray: circumference, strokeDashoffset: dashOffset }}
                      />
                    </svg>
                    <span>{goal.percent}%</span>
                  </div>
                  <div>
                    <h3>{goal.title}</h3>
                    <p>{goal.subtitle}</p>
                  </div>
                </div>
                <div className="ring-totals">
                  <div>
                    <span>Actual</span>
                    <strong>{formatCurrency(goal.current)}</strong>
                  </div>
                  <div>
                    <span>Meta</span>
                    <strong>{formatCurrency(goal.target)}</strong>
                  </div>
                </div>
                {renderGoalActions(goal)}
              </article>
            )
          }

          if (goal.type === 'image') {
            return (
              <article key={goal.id} className="card card-image" style={{ backgroundImage: `url(${goal.image})` }}>
                <div className="overlay" />
                <div className="image-body">
                  <div className="image-top">
                    <span className="material-symbols-outlined">{goal.icon}</span>
                    <span className="chip chip-dark">{goal.percent}%</span>
                  </div>
                  <div>
                    <h3>{goal.title}</h3>
                    <p className="ratio">
                      {formatCurrency(goal.current)} <span>/ {formatCurrency(goal.target)}</span>
                    </p>
                    <small>{goal.eta}</small>
                    {renderGoalActions(goal, true)}
                  </div>
                </div>
              </article>
            )
          }

          return (
            <article key={goal.id} className="card">
              <div className="card-head">
                <div className="icon-box">
                  <span className="material-symbols-outlined">{goal.icon}</span>
                </div>
                <span className="chip">{goal.percent}%</span>
              </div>
              <h3>{goal.title}</h3>
              <p className="ratio">
                {formatCurrency(goal.current)} <span>/ {formatCurrency(goal.target)}</span>
              </p>
              <div className="progress">
                <div style={{ width: `${goal.percent}%` }} />
              </div>
              <small>{goal.eta}</small>
              {renderGoalActions(goal)}
            </article>
          )
        })}

        <button type="button" className="card add-card" onClick={openCreateModal}>
          <div className="add-circle">
            <span className="material-symbols-outlined">add</span>
          </div>
          <h3>Agregar meta</h3>
        </button>
      </section>

      <section className="overview">
        <h3>Resumen de ahorros</h3>
        <div className="overview-top">
          <div>
            <span>Total ahorrado</span>
            <strong>{formatCurrency(totalSaved)}</strong>
          </div>
          <div>
            <span>Neto mensual</span>
            <strong>{formatCurrency(monthlyContribution)}</strong>
          </div>
        </div>
        <div className="mini-bars" aria-hidden="true">
          {[20, 35, 30, 50, 45, 65, 85].map((height, idx) => (
            <div key={`${height}-${idx}`} style={{ height: `${height}%` }} />
          ))}
        </div>
      </section>
      {isLoading && <p className="api-warning">Cargando datos...</p>}

      {createModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Crear meta">
          <div className="modal-card">
            <div className="modal-head">
              <h3>Nueva meta</h3>
              <button type="button" className="icon-btn" onClick={closeCreateModal} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitCreateGoal}>
              <label>
                Nombre
                <input
                  type="text"
                  value={createModal.draft.name}
                  onChange={(e) => updateCreateDraft('name', e.target.value)}
                  disabled={createModal.isSubmitting}
                />
              </label>
              <label>
                Monto objetivo
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={createModal.draft.targetAmount}
                  onChange={(e) => updateCreateDraft('targetAmount', e.target.value)}
                  disabled={createModal.isSubmitting}
                />
              </label>
              <label>
                Fecha objetivo
                <input
                  type="date"
                  value={createModal.draft.targetDate}
                  onChange={(e) => updateCreateDraft('targetDate', e.target.value)}
                  disabled={createModal.isSubmitting}
                />
              </label>
              <label>
                Prioridad
                <select
                  value={createModal.draft.priority}
                  onChange={(e) => updateCreateDraft('priority', e.target.value)}
                  disabled={createModal.isSubmitting}
                >
                  <option value="1">Alta</option>
                  <option value="2">Media</option>
                  <option value="3">Baja</option>
                </select>
              </label>
              <div className="tx-form-actions">
                <button type="button" onClick={closeCreateModal} disabled={createModal.isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={createModal.isSubmitting}>
                  {createModal.isSubmitting ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {contributeModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Aportar a meta">
          <div className="modal-card">
            <div className="modal-head">
              <h3>{`Aportar a ${contributeModal.goalTitle}`}</h3>
              <button type="button" className="icon-btn" onClick={closeContributeModal} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitContribution}>
              <label>
                Monto del aporte
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={contributeModal.amount}
                  onChange={(e) => setContributeModal((prev) => ({ ...prev, amount: e.target.value }))}
                  disabled={contributeModal.isSubmitting}
                />
              </label>
              <div className="tx-form-actions">
                <button type="button" onClick={closeContributeModal} disabled={contributeModal.isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={contributeModal.isSubmitting}>
                  {contributeModal.isSubmitting ? 'Guardando...' : 'Aportar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Screen>
  )
}

function PanelScreen({ metrics, summary, transactions, isLoading, error, userId }) {
  const recentMovements = useMemo(
    () =>
      (transactions || [])
        .slice()
        .sort((a, b) => b.transaction_date.localeCompare(a.transaction_date))
        .slice(0, 5),
    [transactions],
  )

  return (
    <Screen title="Panel" error={error} userId={userId}>
      <section className="balance-hero">
        <p>RESUMEN GENERAL</p>
        <h2>{formatCurrency(metrics.netWorth)}</h2>
        <div className="trend">
          <span className="material-symbols-outlined">insights</span>
          <span>{summary ? `${formatCurrency(Number(summary.net_balance || 0))} este mes` : 'Sin resumen mensual'}</span>
        </div>
        <div className="hero-split">
          <div>
            <span>Activos</span>
            <strong>{formatCurrency(metrics.totalAssets)}</strong>
          </div>
          <div>
            <span>Pasivos</span>
            <strong>{formatCurrency(metrics.totalLiabilities)}</strong>
          </div>
        </div>
      </section>

      <section className="history-card">
        <h3>Ultimos movimientos</h3>
        <div className="tx-list">
          {recentMovements.length === 0 && !isLoading && <p className="api-warning">No hay movimientos para mostrar.</p>}
          {recentMovements.map((tx) => (
            <article key={tx.id} className="tx-item">
              <div className={`tx-icon tone-${transactionTone(tx.transaction_type)}`}>
                <span className="material-symbols-outlined">{transactionIcon(tx.transaction_type)}</span>
              </div>
              <div className="tx-main">
                <h3>{tx.description || formatType(tx.transaction_type)}</h3>
                <p>{formatGroupDate(tx.transaction_date)}</p>
              </div>
              <div className="tx-meta">
                <strong className={tx.transaction_type === 'expense' ? 'neg' : tx.transaction_type === 'income' ? 'pos' : ''}>
                  {`${tx.transaction_type === 'expense' ? '-' : tx.transaction_type === 'income' ? '+' : ''}${formatCurrency(
                    tx.amount,
                    tx.currency || 'COP',
                  )}`}
                </strong>
              </div>
            </article>
          ))}
        </div>
      </section>

      {isLoading && <p className="api-warning">Cargando datos...</p>}
    </Screen>
  )
}

function BudgetsScreen({ transactions, categories, isLoading, error, userId }) {
  const budgetRows = useMemo(() => {
    const currentMonth = new Date().toISOString().slice(0, 7)
    const categoryNames = new Map((categories || []).map((item) => [item.id, item.name]))
    const spentByCategory = new Map()

    ;(transactions || [])
      .filter((tx) => tx.transaction_type === 'expense' && tx.transaction_date?.startsWith(currentMonth))
      .forEach((tx) => {
        const key = tx.category_id || 'uncategorized'
        const current = Number(spentByCategory.get(key) || 0)
        spentByCategory.set(key, current + Number(tx.amount || 0))
      })

    return Array.from(spentByCategory.entries())
      .map(([categoryId, spent]) => ({
        categoryId,
        name: categoryId === 'uncategorized' ? 'Sin categoria' : categoryNames.get(categoryId) || 'Categoria',
        spent,
      }))
      .sort((a, b) => b.spent - a.spent)
      .slice(0, 8)
  }, [transactions, categories])

  return (
    <Screen title="Presupuestos" error={error} userId={userId}>
      <section className="section-head">
        <h2>Control de gasto mensual</h2>
        <p>Vista rapida por categoria para este mes.</p>
      </section>

      <section className="accounts-list">
        {budgetRows.length === 0 && !isLoading && <p className="api-warning">No hay gastos registrados en el mes actual.</p>}
        {budgetRows.map((row) => (
          <article key={row.categoryId} className="account-item">
            <div className="account-main">
              <div className="icon-box tone-orange">
                <span className="material-symbols-outlined">payments</span>
              </div>
              <div>
                <h4>{row.name}</h4>
                <p>Gasto acumulado</p>
              </div>
            </div>
            <div className="account-meta">
              <strong className="neg">{formatCurrency(row.spent)}</strong>
              <span>Mes actual</span>
            </div>
          </article>
        ))}
      </section>

      {isLoading && <p className="api-warning">Cargando presupuestos...</p>}
    </Screen>
  )
}

function JournalScreen({
  transactions,
  isLoading,
  error,
  userId,
  accounts,
  categories,
  fixedTransactions,
  onCreateTransaction,
  onCreateFixedTransaction,
  onUpdateFixedTransaction,
  onDeleteFixedTransaction,
  onCompleteFixedTransaction,
  onOmitFixedTransaction,
}) {
  const [mainFilter, setMainFilter] = useState('Todos')
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [secondaryFilters, setSecondaryFilters] = useState({
    type: 'all',
    status: 'all',
    account: 'all',
    category: 'all',
    currency: 'all',
    dateFrom: '',
    dateTo: '',
  })
  const [isComposerOpen, setIsComposerOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [fixedActionError, setFixedActionError] = useState('')
  const [fixedCrudError, setFixedCrudError] = useState('')
  const [fixedCrudModal, setFixedCrudModal] = useState({
    open: false,
    mode: 'create',
    task: null,
    isSubmitting: false,
    draft: {
      name: '',
      transaction_type: 'expense',
      estimated_amount: '',
      currency: 'COP',
      estimated_date: new Date().toISOString().slice(0, 10),
      category_id: '',
      priority: 'media',
      suggested_source_account_id: '',
      suggested_destination_account_id: '',
      description: '',
    },
  })
  const [fixedModal, setFixedModal] = useState({
    open: false,
    task: null,
    isSubmitting: false,
    error: '',
    draft: {
      realDate: new Date().toISOString().slice(0, 10),
      realAmount: '',
      sourceAccountId: '',
      destinationAccountId: '',
      description: '',
    },
  })
  const [draft, setDraft] = useState({
    transaction_type: 'expense',
    amount: '',
    currency: 'COP',
    account_source_id: '',
    account_destination_id: '',
    category_id: '',
    transaction_date: new Date().toISOString().slice(0, 10),
    description: '',
    status: 'completed',
  })

  useEffect(() => {
    if (!accounts.length) {
      return
    }
    setDraft((prev) => ({
      ...prev,
      account_source_id: prev.account_source_id || accounts[0].id,
      account_destination_id: prev.account_destination_id || accounts[0].id,
    }))
  }, [accounts])

  useEffect(() => {
    if (!categories.length) {
      return
    }
    if (draft.transaction_type === 'transfer') {
      setDraft((prev) => ({ ...prev, category_id: '' }))
      return
    }
    const validCategories = categories.filter((cat) => cat.category_type === draft.transaction_type)
    const selectedIsValid = validCategories.some((cat) => cat.id === draft.category_id)
    if (!selectedIsValid) {
      setDraft((prev) => ({ ...prev, category_id: validCategories[0]?.id || '' }))
    }
  }, [categories, draft.transaction_type, draft.category_id])

  const accountMap = useMemo(() => new Map((accounts || []).map((item) => [item.id, item])), [accounts])
  const categoryMap = useMemo(() => new Map((categories || []).map((item) => [item.id, item])), [categories])

  const categoryOptions = useMemo(() => {
    if (draft.transaction_type === 'transfer') {
      return []
    }
    return categories.filter((cat) => cat.category_type === draft.transaction_type)
  }, [categories, draft.transaction_type])

  const fixedTasks = useMemo(() => {
    return (fixedTransactions || [])
      .map((item) => {
        const category = item.category_id ? categoryMap.get(item.category_id) : null
        return {
          id: item.id,
          sourceKind: 'fixed',
          sourceId: item.id,
          name: item.name,
          type: item.transaction_type,
          amount: Number(item.estimated_amount || 0),
          currency: item.currency || 'COP',
          estimatedDate: item.estimated_date,
          status: item.status || 'pendiente',
          categoryName: category?.name || 'Sin categoría',
          categoryId: item.category_id || null,
          priority: item.priority || 'media',
          sourceAccountId: item.suggested_source_account_id || '',
          destinationAccountId: item.suggested_destination_account_id || '',
          description: item.description || '',
        }
      })
      .sort((a, b) => a.estimatedDate.localeCompare(b.estimatedDate))
  }, [fixedTransactions, categoryMap])

  const dailyTransactions = useMemo(() => {
    return (transactions || [])
      .filter((tx) => tx.source !== 'recurring')
      .map((tx) => {
        const account = accountMap.get(tx.account_id)
        const counterparty = tx.counterparty_account_id ? accountMap.get(tx.counterparty_account_id) : null
        const category = tx.category_id ? categoryMap.get(tx.category_id) : null
        return {
          id: tx.id,
          date: tx.transaction_date,
          type: tx.transaction_type,
          amount: Number(tx.amount || 0),
          currency: tx.currency || account?.currency || 'COP',
          sourceAccountName:
            tx.transaction_type === 'expense' || tx.transaction_type === 'transfer' ? account?.name || 'Sin cuenta' : '',
          destinationAccountName:
            tx.transaction_type === 'income'
              ? account?.name || 'Sin cuenta'
              : tx.transaction_type === 'transfer'
                ? counterparty?.name || 'Sin cuenta'
                : '',
          categoryName: category?.name || 'Sin categoría',
          categoryId: tx.category_id || null,
          description: tx.description || 'Sin descripción',
          status: tx.status || 'completed',
        }
      })
      .sort((a, b) => b.date.localeCompare(a.date))
  }, [transactions, accountMap, categoryMap])

  function updateSecondaryFilter(field, value) {
    setSecondaryFilters((prev) => ({ ...prev, [field]: value }))
  }

  function applyCommonFilters(items, mode) {
    return items.filter((item) => {
      if (secondaryFilters.type !== 'all' && item.type !== secondaryFilters.type) {
        return false
      }
      if (secondaryFilters.status !== 'all' && item.status !== secondaryFilters.status) {
        return false
      }
      if (secondaryFilters.account !== 'all') {
        const matchesAccount = item.sourceAccountId === secondaryFilters.account || item.destinationAccountId === secondaryFilters.account
        if (!matchesAccount) {
          return false
        }
      }
      if (secondaryFilters.category !== 'all' && item.categoryId !== secondaryFilters.category) {
        return false
      }
      if (secondaryFilters.currency !== 'all' && item.currency !== secondaryFilters.currency) {
        return false
      }
      const dateValue = mode === 'fixed' ? item.estimatedDate : item.date
      if (secondaryFilters.dateFrom && dateValue < secondaryFilters.dateFrom) {
        return false
      }
      if (secondaryFilters.dateTo && dateValue > secondaryFilters.dateTo) {
        return false
      }
      return true
    })
  }

  const fixedTasksFiltered = useMemo(() => {
    let data = fixedTasks
    return applyCommonFilters(data, 'fixed')
  }, [fixedTasks, mainFilter, secondaryFilters])

  const dailyTransactionsFiltered = useMemo(() => {
    let data = dailyTransactions
    return applyCommonFilters(data, 'daily')
  }, [dailyTransactions, mainFilter, secondaryFilters])

  const listTitle =
    mainFilter === 'Transacciones fijas'
      ? 'Tareas fijas del mes'
      : mainFilter === 'Transacciones recurrentes'
        ? 'Transacciones del día a día'
        : 'Movimientos'

  const showFixedSection = mainFilter === 'Transacciones fijas'
  const showDailySection = mainFilter === 'Transacciones recurrentes'

  const mixedMovements = useMemo(() => {
    if (mainFilter !== 'Todos') {
      return []
    }
    // "Todos" should list only real transactions. Fixed tasks are reminders
    // and become transactions only after completion.
    const dailyItems = dailyTransactionsFiltered.map((item) => ({
      id: `mix-daily-${item.id}`,
      module: 'recurrente',
      date: item.date,
      type: item.type,
      amount: item.amount,
      currency: item.currency,
      title: item.description || 'Transacción',
      source: item.sourceAccountName || '',
      destination: item.destinationAccountName || '',
      status: '',
      categoryName: item.categoryName,
      description: '',
    }))
    return dailyItems.sort((a, b) => b.date.localeCompare(a.date))
  }, [mainFilter, dailyTransactionsFiltered])

  function openComposer() {
    setSubmitError('')
    setIsComposerOpen(true)
  }

  function closeComposer() {
    if (isSubmitting) {
      return
    }
    setIsComposerOpen(false)
  }

  function updateDraft(field, value) {
    setDraft((prev) => ({ ...prev, [field]: value }))
  }

  function openFixedModal(task) {
    setFixedActionError('')
    setFixedModal({
      open: true,
      task,
      isSubmitting: false,
      error: '',
      draft: {
        realDate: new Date().toISOString().slice(0, 10),
        realAmount: String(task.amount || ''),
        sourceAccountId: task.sourceAccountId || accounts[0]?.id || '',
        destinationAccountId: task.destinationAccountId || accounts[0]?.id || '',
        description: task.description || task.name,
      },
    })
  }

  function openFixedCrudModal(mode, task = null) {
    setFixedCrudError('')
    const draft = task
      ? {
          name: task.name,
          transaction_type: task.type,
          estimated_amount: String(task.amount),
          currency: task.currency,
          estimated_date: task.estimatedDate,
          category_id: task.categoryId || '',
          priority: task.priority || 'media',
          suggested_source_account_id: task.sourceAccountId || '',
          suggested_destination_account_id: task.destinationAccountId || '',
          description: task.description || '',
        }
      : {
          name: '',
          transaction_type: 'expense',
          estimated_amount: '',
          currency: 'COP',
          estimated_date: new Date().toISOString().slice(0, 10),
          category_id: '',
          priority: 'media',
          suggested_source_account_id: accounts[0]?.id || '',
          suggested_destination_account_id: '',
          description: '',
        }
    setFixedCrudModal({
      open: true,
      mode,
      task,
      isSubmitting: false,
      draft,
    })
  }

  function closeFixedCrudModal() {
    if (fixedCrudModal.isSubmitting) return
    setFixedCrudModal((prev) => ({ ...prev, open: false }))
  }

  function updateFixedCrudDraft(field, value) {
    setFixedCrudModal((prev) => ({
      ...prev,
      draft: {
        ...prev.draft,
        [field]: value,
      },
    }))
  }

  function closeFixedModal() {
    if (fixedModal.isSubmitting) {
      return
    }
    setFixedModal((prev) => ({ ...prev, open: false, error: '' }))
  }

  function updateFixedModalDraft(field, value) {
    setFixedModal((prev) => ({
      ...prev,
      draft: {
        ...prev.draft,
        [field]: value,
      },
    }))
  }

  async function submitFixedModal(event) {
    event.preventDefault()
    if (!fixedModal.task) {
      return
    }
    const task = fixedModal.task
    const amount = Number(fixedModal.draft.realAmount)
    if (!amount || amount <= 0) {
      setFixedModal((prev) => ({ ...prev, error: 'El monto real debe ser mayor a cero.' }))
      return
    }
    if (task.type === 'income' && !fixedModal.draft.destinationAccountId) {
      setFixedModal((prev) => ({ ...prev, error: 'Selecciona una cuenta destino.' }))
      return
    }
    if (task.type === 'expense' && !fixedModal.draft.sourceAccountId) {
      setFixedModal((prev) => ({ ...prev, error: 'Selecciona una cuenta origen.' }))
      return
    }
    if (task.type === 'transfer') {
      if (!fixedModal.draft.sourceAccountId || !fixedModal.draft.destinationAccountId) {
        setFixedModal((prev) => ({ ...prev, error: 'Selecciona cuenta origen y destino.' }))
        return
      }
      if (fixedModal.draft.sourceAccountId === fixedModal.draft.destinationAccountId) {
        setFixedModal((prev) => ({ ...prev, error: 'La cuenta origen y destino no pueden ser la misma.' }))
        return
      }
    }

    try {
      setFixedModal((prev) => ({ ...prev, isSubmitting: true, error: '' }))
      await onCompleteFixedTransaction(task.sourceId, {
        real_date: fixedModal.draft.realDate,
        real_amount: amount,
        source_account_id: fixedModal.draft.sourceAccountId || null,
        destination_account_id: fixedModal.draft.destinationAccountId || null,
        description: fixedModal.draft.description.trim() || task.name,
      })
      closeFixedModal()
    } catch (_error) {
      setFixedModal((prev) => ({ ...prev, error: 'No se pudo completar la tarea fija.' }))
    } finally {
      setFixedModal((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  async function omitFixedTask(task) {
    try {
      setFixedActionError('')
      await onOmitFixedTransaction(task.sourceId)
    } catch (_error) {
      setFixedActionError('No se pudo omitir la tarea fija.')
    }
  }

  async function submitFixedCrud(event) {
    event.preventDefault()
    setFixedCrudError('')
    const amount = Number(fixedCrudModal.draft.estimated_amount)
    if (!fixedCrudModal.draft.name.trim()) {
      setFixedCrudError('El nombre es obligatorio.')
      return
    }
    if (!amount || amount <= 0) {
      setFixedCrudError('El monto estimado debe ser mayor a cero.')
      return
    }
    const txType = fixedCrudModal.draft.transaction_type
    if ((txType === 'expense' || txType === 'transfer') && !fixedCrudModal.draft.suggested_source_account_id) {
      setFixedCrudError('Selecciona cuenta origen sugerida.')
      return
    }
    if ((txType === 'income' || txType === 'transfer') && !fixedCrudModal.draft.suggested_destination_account_id) {
      setFixedCrudError('Selecciona cuenta destino sugerida.')
      return
    }
    if (
      txType === 'transfer' &&
      fixedCrudModal.draft.suggested_source_account_id === fixedCrudModal.draft.suggested_destination_account_id
    ) {
      setFixedCrudError('La cuenta origen y destino sugeridas no pueden ser iguales.')
      return
    }

    const payload = {
      name: fixedCrudModal.draft.name.trim(),
      transaction_type: txType,
      estimated_amount: amount,
      currency: fixedCrudModal.draft.currency,
      estimated_date: fixedCrudModal.draft.estimated_date,
      category_id: fixedCrudModal.draft.category_id || null,
      priority: fixedCrudModal.draft.priority,
      suggested_source_account_id: fixedCrudModal.draft.suggested_source_account_id || null,
      suggested_destination_account_id: fixedCrudModal.draft.suggested_destination_account_id || null,
      description: fixedCrudModal.draft.description.trim() || null,
    }
    try {
      setFixedCrudModal((prev) => ({ ...prev, isSubmitting: true }))
      if (fixedCrudModal.mode === 'create') {
        await onCreateFixedTransaction(payload)
      } else if (fixedCrudModal.task) {
        await onUpdateFixedTransaction(fixedCrudModal.task.sourceId, payload)
      }
      closeFixedCrudModal()
    } catch (_error) {
      setFixedCrudError('No se pudo guardar la transacción fija.')
    } finally {
      setFixedCrudModal((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  async function submitDraft(event) {
    event.preventDefault()
    setSubmitError('')

    const numericAmount = Number(draft.amount)
    if (!numericAmount || numericAmount <= 0) {
      setSubmitError('El monto debe ser mayor a cero.')
      return
    }
    if (draft.transaction_type === 'income' && !draft.account_destination_id) {
      setSubmitError('Para ingresos debes seleccionar cuenta destino.')
      return
    }
    if (draft.transaction_type === 'expense' && !draft.account_source_id) {
      setSubmitError('Para gastos debes seleccionar cuenta origen.')
      return
    }
    if (draft.transaction_type === 'transfer') {
      if (!draft.account_source_id || !draft.account_destination_id) {
        setSubmitError('Para transferencias debes seleccionar cuenta origen y destino.')
        return
      }
      if (draft.account_source_id === draft.account_destination_id) {
        setSubmitError('La cuenta origen y destino no pueden ser la misma.')
        return
      }
    }

    try {
      setIsSubmitting(true)
      const payload = {
        transaction_type: draft.transaction_type,
        amount: numericAmount,
        currency: draft.currency,
        transaction_date: draft.transaction_date,
        description: draft.description.trim() || null,
        status: draft.status,
        category_id: draft.transaction_type === 'transfer' ? null : draft.category_id || null,
      }

      if (draft.transaction_type === 'income') {
        payload.account_id = draft.account_destination_id
      } else if (draft.transaction_type === 'expense') {
        payload.account_id = draft.account_source_id
      } else {
        payload.account_id = draft.account_source_id
        payload.counterparty_account_id = draft.account_destination_id
      }

      await onCreateTransaction(payload)
      setIsComposerOpen(false)
      setDraft((prev) => ({
        ...prev,
        amount: '',
        description: '',
      }))
    } catch (_error) {
      setSubmitError('No se pudo crear la transacción. Verifica los datos e intenta de nuevo.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Screen title="Diario" error={error} userId={userId}>
      <section className="search-area">
        <div className="chip-row">
          {['Todos', 'Transacciones fijas', 'Transacciones recurrentes'].map((chip) => (
            <button
              type="button"
              key={chip}
              className={`filter-chip ${chip === mainFilter ? 'active' : ''}`}
              onClick={() => setMainFilter(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
        <button type="button" className="advanced-toggle" onClick={() => setShowAdvancedFilters((prev) => !prev)}>
          {showAdvancedFilters ? 'Ocultar filtros avanzados' : 'Filtros avanzados'}
        </button>
        {showAdvancedFilters && (
          <div className="secondary-filters">
            <select value={secondaryFilters.type} onChange={(e) => updateSecondaryFilter('type', e.target.value)}>
              <option value="all">Tipo: todos</option>
              <option value="income">Tipo: ingreso</option>
              <option value="expense">Tipo: gasto</option>
              <option value="transfer">Tipo: transferencia</option>
            </select>
            {mainFilter !== 'Transacciones recurrentes' && (
              <select value={secondaryFilters.status} onChange={(e) => updateSecondaryFilter('status', e.target.value)}>
                <option value="all">Estado: todos</option>
                <option value="pendiente">Estado: pendiente</option>
                <option value="completada">Estado: completada</option>
                <option value="omitida">Estado: omitida</option>
              </select>
            )}
            <select value={secondaryFilters.account} onChange={(e) => updateSecondaryFilter('account', e.target.value)}>
              <option value="all">Cuenta: todas</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
            <select value={secondaryFilters.category} onChange={(e) => updateSecondaryFilter('category', e.target.value)}>
              <option value="all">Categoría: todas</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <select value={secondaryFilters.currency} onChange={(e) => updateSecondaryFilter('currency', e.target.value)}>
              <option value="all">Moneda: todas</option>
              <option value="COP">COP</option>
              <option value="USD">USD</option>
            </select>
            <input type="date" value={secondaryFilters.dateFrom} onChange={(e) => updateSecondaryFilter('dateFrom', e.target.value)} />
            <input type="date" value={secondaryFilters.dateTo} onChange={(e) => updateSecondaryFilter('dateTo', e.target.value)} />
          </div>
        )}
      </section>

      {mainFilter === 'Todos' && (
        <section className="fixed-expenses">
          <div className="fixed-head">
            <h3>{listTitle}</h3>
            <span>{mixedMovements.length} resultados</span>
          </div>
          {mixedMovements.length === 0 && <p className="api-warning">No hay movimientos con los filtros actuales.</p>}
          {mixedMovements.map((item) => (
            <article key={item.id} className="tx-item recurring-item">
              <div className={`tx-icon tone-${transactionTone(item.type)}`}>
                <span className="material-symbols-outlined">{transactionIcon(item.type)}</span>
              </div>
              <div className="tx-main">
                <h3>{item.title}</h3>
                <p>{`${item.module === 'fija' ? 'Fija' : 'Recurrente'} · ${formatType(item.type)} · ${item.categoryName}`}</p>
                {item.source && <p>{`Sale de: ${item.source}`}</p>}
                {item.destination && <p>{`Entra a: ${item.destination}`}</p>}
                {item.module === 'fija' && <p>{`Estado: ${item.status}`}</p>}
              </div>
              <div className="tx-meta">
                <strong className={item.type === 'expense' ? 'neg' : item.type === 'income' ? 'pos' : ''}>
                  {`${item.type === 'expense' ? '-' : item.type === 'income' ? '+' : ''}${formatCurrency(item.amount, item.currency)}`}
                </strong>
                <span>{formatDayMonth(item.date)}</span>
              </div>
            </article>
          ))}
        </section>
      )}

      {showFixedSection && (
        <section className="fixed-expenses">
          <div className="fixed-head">
            <h3>Tareas fijas del mes</h3>
            <span>{fixedTasksFiltered.length} resultados</span>
          </div>
          <div className="fixed-toolbar">
            <button type="button" className="small-btn" onClick={() => openFixedCrudModal('create')}>
              + Nueva fija
            </button>
          </div>
          {fixedTasksFiltered.length === 0 && <p className="api-warning">No hay tareas fijas con los filtros actuales.</p>}
          {fixedTasksFiltered.map((task) => (
            <article key={task.id} className={`fixed-item ${task.status === 'completada' ? 'done' : ''}`}>
              <div className="fixed-main">
                <h4>{task.name}</h4>
                <p>{`${formatCurrency(task.amount, task.currency)} · ${task.type} · ${task.categoryName}`}</p>
                <p>{`Fecha estimada: ${formatDayMonth(task.estimatedDate)} · Estado: ${task.status}`}</p>
                <p>{`Prioridad: ${task.priority}`}</p>
                {task.sourceAccountId && <p>{`Cuenta origen sugerida: ${accountMap.get(task.sourceAccountId)?.name || 'Sin cuenta'}`}</p>}
                {task.destinationAccountId && (
                  <p>{`Cuenta destino sugerida: ${accountMap.get(task.destinationAccountId)?.name || 'Sin cuenta'}`}</p>
                )}
              </div>
              <div className="fixed-actions fixed-actions-stack">
                {task.status === 'pendiente' && (
                  <>
                    <button type="button" onClick={() => openFixedModal(task)}>
                      Completar
                    </button>
                    <button type="button" className="ghost" onClick={() => omitFixedTask(task)}>
                      Omitir
                    </button>
                    <button type="button" className="ghost" onClick={() => openFixedCrudModal('edit', task)}>
                      Editar
                    </button>
                    <button
                      type="button"
                      className="ghost"
                      onClick={async () => {
                        try {
                          await onDeleteFixedTransaction(task.sourceId)
                        } catch (_error) {
                          setFixedActionError('No se pudo eliminar la tarea fija.')
                        }
                      }}
                    >
                      Eliminar
                    </button>
                  </>
                )}
                {task.status === 'completada' && <span className="chip fixed-chip">Completada</span>}
                {task.status === 'omitida' && <span className="chip">Omitida</span>}
              </div>
            </article>
          ))}
          {fixedActionError && <p className="api-warning">{fixedActionError}</p>}
        </section>
      )}

      {showDailySection && (
        <section className="fixed-expenses">
          <div className="fixed-head">
            <h3>Transacciones recurrentes día a día</h3>
            <span>{dailyTransactionsFiltered.length} resultados</span>
          </div>
          {dailyTransactionsFiltered.length === 0 && (
            <p className="api-warning">No hay transacciones día a día con los filtros actuales.</p>
          )}
          {dailyTransactionsFiltered.map((tx) => (
            <article className="tx-item recurring-item" key={tx.id}>
              <div className={`tx-icon tone-${transactionTone(tx.type)}`}>
                <span className="material-symbols-outlined">{transactionIcon(tx.type)}</span>
              </div>
              <div className="tx-main">
                <h3>{tx.description}</h3>
                <p>{`${formatType(tx.type)} · ${tx.categoryName} · ${formatGroupDate(tx.date)}`}</p>
                {tx.sourceAccountName && <p>{`Sale de: ${tx.sourceAccountName}`}</p>}
                {tx.destinationAccountName && <p>{`Entra a: ${tx.destinationAccountName}`}</p>}
              </div>
              <div className="tx-meta">
                <strong className={tx.type === 'expense' ? 'neg' : tx.type === 'income' ? 'pos' : ''}>
                  {`${tx.type === 'expense' ? '-' : tx.type === 'income' ? '+' : ''}${formatCurrency(tx.amount, tx.currency)}`}
                </strong>
                <span>{tx.status}</span>
              </div>
            </article>
          ))}
        </section>
      )}

      {isLoading && <p className="api-warning">Cargando transacciones...</p>}

      <button type="button" className="fab" aria-label="Nueva transacción" onClick={openComposer}>
        <span className="material-symbols-outlined">add</span>
      </button>

      {isComposerOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Agregar transacción">
          <div className="modal-card">
            <div className="modal-head">
              <h3>Nueva transacción recurrente</h3>
              <button type="button" className="icon-btn" onClick={closeComposer} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitDraft}>
              <label>
                Tipo
                <select
                  value={draft.transaction_type}
                  onChange={(e) => updateDraft('transaction_type', e.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="expense">Gasto</option>
                  <option value="income">Ingreso</option>
                  <option value="transfer">Transferencia</option>
                </select>
              </label>
              <label>
                Monto
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={draft.amount}
                  onChange={(e) => updateDraft('amount', e.target.value)}
                  placeholder="0.00"
                  disabled={isSubmitting}
                />
              </label>
              <label>
                Moneda
                <select value={draft.currency} onChange={(e) => updateDraft('currency', e.target.value)} disabled={isSubmitting}>
                  <option value="COP">COP</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              {(draft.transaction_type === 'expense' || draft.transaction_type === 'transfer') && (
                <label>
                  Cuenta origen
                <select
                  value={draft.account_source_id}
                  onChange={(e) => updateDraft('account_source_id', e.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="">Selecciona cuenta</option>
                  {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                  </select>
                </label>
              )}
              {(draft.transaction_type === 'income' || draft.transaction_type === 'transfer') && (
                <label>
                  Cuenta destino
                <select
                  value={draft.account_destination_id}
                  onChange={(e) => updateDraft('account_destination_id', e.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="">Selecciona cuenta</option>
                  {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                  </select>
                </label>
              )}
              {draft.transaction_type !== 'transfer' && (
                <label>
                  Categoría
                  <select value={draft.category_id} onChange={(e) => updateDraft('category_id', e.target.value)} disabled={isSubmitting}>
                    <option value="">Sin categoría</option>
                    {categoryOptions.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                Fecha
                <input
                  type="date"
                  value={draft.transaction_date}
                  onChange={(e) => updateDraft('transaction_date', e.target.value)}
                  disabled={isSubmitting}
                />
              </label>
              <label>
                Descripción
                <input
                  type="text"
                  maxLength={500}
                  value={draft.description}
                  onChange={(e) => updateDraft('description', e.target.value)}
                  placeholder="Ej: Almuerzo, gasolina, ingreso extra"
                  disabled={isSubmitting}
                />
              </label>
              {submitError && <p className="api-warning">{submitError}</p>}
              <div className="tx-form-actions">
                <button type="button" onClick={closeComposer} disabled={isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Guardando...' : 'Guardar transacción'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {fixedModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Completar tarea fija">
          <div className="modal-card">
            <div className="modal-head">
              <h3>Completar tarea fija</h3>
              <button type="button" className="icon-btn" onClick={closeFixedModal} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitFixedModal}>
              <label>
                Fecha real
                <input
                  type="date"
                  value={fixedModal.draft.realDate}
                  onChange={(e) => updateFixedModalDraft('realDate', e.target.value)}
                  disabled={fixedModal.isSubmitting}
                />
              </label>
              <label>
                Monto real
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={fixedModal.draft.realAmount}
                  onChange={(e) => updateFixedModalDraft('realAmount', e.target.value)}
                  disabled={fixedModal.isSubmitting}
                />
              </label>
              {(fixedModal.task?.type === 'expense' || fixedModal.task?.type === 'transfer') && (
                <label>
                  Cuenta origen
                  <select
                    value={fixedModal.draft.sourceAccountId}
                    onChange={(e) => updateFixedModalDraft('sourceAccountId', e.target.value)}
                    disabled={fixedModal.isSubmitting}
                  >
                    <option value="">Selecciona cuenta</option>
                    {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {(fixedModal.task?.type === 'income' || fixedModal.task?.type === 'transfer') && (
                <label>
                  Cuenta destino
                  <select
                    value={fixedModal.draft.destinationAccountId}
                    onChange={(e) => updateFixedModalDraft('destinationAccountId', e.target.value)}
                    disabled={fixedModal.isSubmitting}
                  >
                    <option value="">Selecciona cuenta</option>
                    {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                Descripción
                <input
                  type="text"
                  maxLength={500}
                  value={fixedModal.draft.description}
                  onChange={(e) => updateFixedModalDraft('description', e.target.value)}
                  disabled={fixedModal.isSubmitting}
                />
              </label>
              {fixedModal.error && <p className="api-warning">{fixedModal.error}</p>}
              <div className="tx-form-actions">
                <button type="button" onClick={closeFixedModal} disabled={fixedModal.isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={fixedModal.isSubmitting}>
                  {fixedModal.isSubmitting ? 'Confirmando...' : 'Confirmar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {fixedCrudModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Formulario transacción fija">
          <div className="modal-card">
            <div className="modal-head">
              <h3>{fixedCrudModal.mode === 'create' ? 'Nueva transacción fija' : 'Editar transacción fija'}</h3>
              <button type="button" className="icon-btn" onClick={closeFixedCrudModal} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitFixedCrud}>
              <label>
                Nombre
                <input
                  type="text"
                  value={fixedCrudModal.draft.name}
                  onChange={(e) => updateFixedCrudDraft('name', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                />
              </label>
              <label>
                Tipo
                <select
                  value={fixedCrudModal.draft.transaction_type}
                  onChange={(e) => updateFixedCrudDraft('transaction_type', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="income">Ingreso</option>
                  <option value="expense">Gasto</option>
                  <option value="transfer">Transferencia</option>
                </select>
              </label>
              <label>
                Monto estimado
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={fixedCrudModal.draft.estimated_amount}
                  onChange={(e) => updateFixedCrudDraft('estimated_amount', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                />
              </label>
              <label>
                Moneda
                <select
                  value={fixedCrudModal.draft.currency}
                  onChange={(e) => updateFixedCrudDraft('currency', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="COP">COP</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              <label>
                Fecha estimada
                <input
                  type="date"
                  value={fixedCrudModal.draft.estimated_date}
                  onChange={(e) => updateFixedCrudDraft('estimated_date', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                />
              </label>
              <label>
                Categoría
                <select
                  value={fixedCrudModal.draft.category_id}
                  onChange={(e) => updateFixedCrudDraft('category_id', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="">Sin categoría</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Prioridad
                <select
                  value={fixedCrudModal.draft.priority}
                  onChange={(e) => updateFixedCrudDraft('priority', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="alta">Alta</option>
                  <option value="media">Media</option>
                  <option value="baja">Baja</option>
                </select>
              </label>
              <label>
                Cuenta origen sugerida
                <select
                  value={fixedCrudModal.draft.suggested_source_account_id}
                  onChange={(e) => updateFixedCrudDraft('suggested_source_account_id', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="">Sin cuenta</option>
                  {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Cuenta destino sugerida
                <select
                  value={fixedCrudModal.draft.suggested_destination_account_id}
                  onChange={(e) => updateFixedCrudDraft('suggested_destination_account_id', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                >
                  <option value="">Sin cuenta</option>
                  {accounts.length === 0 && <option value="" disabled>No hay cuentas disponibles</option>}
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Descripción
                <input
                  type="text"
                  value={fixedCrudModal.draft.description}
                  onChange={(e) => updateFixedCrudDraft('description', e.target.value)}
                  disabled={fixedCrudModal.isSubmitting}
                />
              </label>
              {fixedCrudError && <p className="api-warning">{fixedCrudError}</p>}
              <div className="tx-form-actions">
                <button type="button" onClick={closeFixedCrudModal} disabled={fixedCrudModal.isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={fixedCrudModal.isSubmitting}>
                  {fixedCrudModal.isSubmitting ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Screen>
  )
}

function AccountsScreen({
  accounts,
  metrics,
  summary,
  transactions,
  isLoading,
  error,
  userId,
  onCreateAccount,
  onUpdateAccount,
  onDeactivateAccount,
}) {
  const [accountModal, setAccountModal] = useState({
    open: false,
    mode: 'create',
    accountId: '',
    isSubmitting: false,
    error: '',
    draft: {
      name: '',
      account_type: 'savings',
      institution_name: '',
      currency: 'COP',
      initial_balance: '0',
    },
  })
  const [selectedAccountId, setSelectedAccountId] = useState('')

  const accountRows = accounts.length
    ? accounts.map((acc) => ({
        id: acc.id,
        name: acc.name,
        type: formatType(acc.account_type),
        amount: Number(acc.current_balance || 0),
        initialBalance: Number(acc.initial_balance || 0),
        note: acc.account_type === 'credit_card' ? 'Línea de crédito' : 'Activa',
        icon: accountIcon(acc.account_type),
        tone: Number(acc.current_balance || 0) < 0 ? 'red' : 'green',
        institution: acc.institution_name || '',
        currency: acc.currency || 'COP',
      }))
    : []

  const selectedAccount = useMemo(
    () => accountRows.find((item) => item.id === selectedAccountId) || null,
    [accountRows, selectedAccountId],
  )
  const selectedAccountMovements = useMemo(() => {
    if (!selectedAccountId) return []
    return (transactions || [])
      .filter((tx) => tx.account_id === selectedAccountId || tx.counterparty_account_id === selectedAccountId)
      .sort((a, b) => b.transaction_date.localeCompare(a.transaction_date))
      .slice(0, 20)
  }, [transactions, selectedAccountId])

  function openAccountModal(mode, account = null) {
    setAccountModal({
      open: true,
      mode,
      accountId: account?.id || '',
      isSubmitting: false,
      error: '',
      draft: account
        ? {
            name: account.name,
            account_type: account.account_type || 'savings',
            institution_name: account.institution_name || '',
            currency: account.currency || 'COP',
            initial_balance: String(account.initial_balance || 0),
          }
        : {
            name: '',
            account_type: 'savings',
            institution_name: '',
            currency: 'COP',
            initial_balance: '0',
          },
    })
  }

  function closeAccountModal() {
    if (accountModal.isSubmitting) return
    setAccountModal((prev) => ({ ...prev, open: false }))
  }

  function updateAccountDraft(field, value) {
    setAccountModal((prev) => ({
      ...prev,
      draft: {
        ...prev.draft,
        [field]: value,
      },
    }))
  }

  async function submitAccountModal(event) {
    event.preventDefault()
    const initialBalance = Number(accountModal.draft.initial_balance)
    if (!accountModal.draft.name.trim()) {
      setAccountModal((prev) => ({ ...prev, error: 'El nombre es obligatorio.' }))
      return
    }
    if (Number.isNaN(initialBalance) || initialBalance < 0) {
      setAccountModal((prev) => ({ ...prev, error: 'El saldo inicial debe ser 0 o mayor.' }))
      return
    }
    try {
      setAccountModal((prev) => ({ ...prev, isSubmitting: true, error: '' }))
      const payload = {
        name: accountModal.draft.name.trim(),
        account_type: accountModal.draft.account_type,
        institution_name: accountModal.draft.institution_name.trim() || null,
        currency: accountModal.draft.currency,
        initial_balance: initialBalance,
      }
      if (accountModal.mode === 'create') {
        await onCreateAccount(payload)
      } else {
        await onUpdateAccount(accountModal.accountId, {
          name: payload.name,
          institution_name: payload.institution_name,
        })
      }
      closeAccountModal()
    } catch (_error) {
      setAccountModal((prev) => ({ ...prev, error: 'No se pudo guardar la cuenta.' }))
    } finally {
      setAccountModal((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  return (
    <Screen title="Cuentas" error={error} userId={userId}>
      <section className="balance-hero">
        <p>PATRIMONIO NETO TOTAL</p>
        <h2>{formatCurrency(metrics.netWorth)}</h2>
        <div className="trend">
          <span className="material-symbols-outlined">trending_up</span>
          <span>
            {summary ? `${formatCurrency(Number(summary.net_balance || 0))} este mes` : 'Resumen mensual'}
          </span>
        </div>
        <div className="hero-split">
          <div>
            <span>Activos totales</span>
            <strong>{formatCurrency(metrics.totalAssets)}</strong>
          </div>
          <div>
            <span>Pasivos totales</span>
            <strong>{formatCurrency(metrics.totalLiabilities)}</strong>
          </div>
        </div>
      </section>

      <section className="portfolio-head">
        <h3>Desglose del portafolio</h3>
        <button type="button" onClick={() => openAccountModal('create')}>
          + NUEVA CUENTA
        </button>
      </section>

      <section className="accounts-list">
        {accountRows.length === 0 && !isLoading && <p className="api-warning">No hay cuentas para este usuario.</p>}
        {accountRows.map((account) => (
          <article
            key={account.id}
            className="account-item"
            onClick={() => setSelectedAccountId(account.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter') setSelectedAccountId(account.id)
            }}
          >
            <div className="account-main">
              <div className={`icon-box tone-${account.tone}`}>
                <span className="material-symbols-outlined">{account.icon}</span>
              </div>
              <div>
                <h4>{account.name}</h4>
                <p>{account.type}</p>
              </div>
            </div>
            <div className="account-meta">
              <strong className={account.amount < 0 ? 'neg' : ''}>{formatSignedCurrency(account.amount)}</strong>
              <span>{account.note}</span>
            </div>
            <div className="fixed-actions fixed-actions-stack">
              <button
                type="button"
                className="ghost"
                onClick={(event) => {
                  event.stopPropagation()
                  const raw = accounts.find((acc) => acc.id === account.id)
                  openAccountModal('edit', raw)
                }}
              >
                Editar
              </button>
              <button
                type="button"
                className="ghost"
                onClick={async (event) => {
                  event.stopPropagation()
                  try {
                    await onDeactivateAccount(account.id)
                    if (selectedAccountId === account.id) {
                      setSelectedAccountId('')
                    }
                  } catch (_error) {
                    // Error shown in main screen warning
                  }
                }}
              >
                Desactivar
              </button>
            </div>
          </article>
        ))}
      </section>

      {selectedAccount && (
        <section className="history-card">
          <h3>{`Detalle ${selectedAccount.name}`}</h3>
          <p>{`${selectedAccount.institution || 'Sin institución'} · ${selectedAccount.currency}`}</p>
          <p>{`Saldo inicial: ${formatCurrency(selectedAccount.initialBalance, selectedAccount.currency)}`}</p>
          <p>{`Saldo actual: ${formatCurrency(selectedAccount.amount, selectedAccount.currency)}`}</p>
          <div className="tx-list">
            {selectedAccountMovements.map((tx) => (
              <article key={tx.id} className="tx-item">
                <div className={`tx-icon tone-${transactionTone(tx.transaction_type)}`}>
                  <span className="material-symbols-outlined">{transactionIcon(tx.transaction_type)}</span>
                </div>
                <div className="tx-main">
                  <h3>{tx.description || formatType(tx.transaction_type)}</h3>
                  <p>{formatGroupDate(tx.transaction_date)}</p>
                </div>
                <div className="tx-meta">
                  <strong className={tx.transaction_type === 'expense' ? 'neg' : tx.transaction_type === 'income' ? 'pos' : ''}>
                    {`${tx.transaction_type === 'expense' ? '-' : tx.transaction_type === 'income' ? '+' : ''}${formatCurrency(
                      tx.amount,
                      tx.currency || selectedAccount.currency,
                    )}`}
                  </strong>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="history-card">
        <h3>Historial de saldo</h3>
        <div className="mini-bars" aria-hidden="true">
          {[40, 45, 42, 55, 62, 75, 85].map((height, idx) => (
            <div key={`${height}-${idx}`} style={{ height: `${height}%` }} />
          ))}
        </div>
      </section>

      {isLoading && <p className="api-warning">Cargando cuentas...</p>}

      <button type="button" className="fab" aria-label="Agregar cuenta" onClick={() => openAccountModal('create')}>
        <span className="material-symbols-outlined">add</span>
      </button>

      {accountModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Formulario cuenta">
          <div className="modal-card">
            <div className="modal-head">
              <h3>{accountModal.mode === 'create' ? 'Nueva cuenta' : 'Editar cuenta'}</h3>
              <button type="button" className="icon-btn" onClick={closeAccountModal} aria-label="Cerrar">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <form className="tx-form" onSubmit={submitAccountModal}>
              <label>
                Nombre
                <input
                  type="text"
                  value={accountModal.draft.name}
                  onChange={(e) => updateAccountDraft('name', e.target.value)}
                  disabled={accountModal.isSubmitting}
                />
              </label>
              <label>
                Tipo
                <select
                  value={accountModal.draft.account_type}
                  onChange={(e) => updateAccountDraft('account_type', e.target.value)}
                  disabled={accountModal.isSubmitting || accountModal.mode === 'edit'}
                >
                  <option value="bank">Banco</option>
                  <option value="cash">Efectivo</option>
                  <option value="credit_card">Tarjeta de crédito</option>
                  <option value="digital_wallet">Billetera digital</option>
                  <option value="investment">Inversión</option>
                  <option value="savings">Ahorros</option>
                </select>
              </label>
              <label>
                Institución
                <input
                  type="text"
                  value={accountModal.draft.institution_name}
                  onChange={(e) => updateAccountDraft('institution_name', e.target.value)}
                  disabled={accountModal.isSubmitting}
                />
              </label>
              <label>
                Moneda
                <select
                  value={accountModal.draft.currency}
                  onChange={(e) => updateAccountDraft('currency', e.target.value)}
                  disabled={accountModal.isSubmitting || accountModal.mode === 'edit'}
                >
                  <option value="COP">COP</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              <label>
                Saldo inicial
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={accountModal.draft.initial_balance}
                  onChange={(e) => updateAccountDraft('initial_balance', e.target.value)}
                  disabled={accountModal.isSubmitting || accountModal.mode === 'edit'}
                />
              </label>
              {accountModal.error && <p className="api-warning">{accountModal.error}</p>}
              <div className="tx-form-actions">
                <button type="button" onClick={closeAccountModal} disabled={accountModal.isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={accountModal.isSubmitting}>
                  {accountModal.isSubmitting ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Screen>
  )
}

function groupTransactionsByDate(transactions) {
  if (!Array.isArray(transactions) || transactions.length === 0) {
    return []
  }

  const grouped = new Map()

  transactions.forEach((tx) => {
    const key = tx.transaction_date
    if (!grouped.has(key)) {
      grouped.set(key, [])
    }
    grouped.get(key).push(tx)
  })

  return Array.from(grouped.entries()).map(([dateKey, items]) => {
    const currencies = new Set(items.map((tx) => tx.currency || 'COP'))
    const dayCurrency = currencies.size === 1 ? (items[0]?.currency || 'COP') : null
    const dayTotal = items.reduce((sum, tx) => {
      const amount = Number(tx.amount || 0)
      if (tx.transaction_type === 'expense') {
        return sum - amount
      }
      if (tx.transaction_type === 'income') {
        return sum + amount
      }
      return sum
    }, 0)

    return {
      day: formatGroupDate(dateKey),
      total: dayCurrency ? formatSignedCurrency(dayTotal, dayCurrency) : 'Total mixto',
      items: items.map((tx) => {
        const amount = Number(tx.amount || 0)
        const kind = tx.transaction_type
        const sign = kind === 'expense' ? '-' : kind === 'income' ? '+' : ''
        const currency = tx.currency || 'COP'

        return {
          name: tx.description || formatType(kind),
          details: `${formatType(kind)} • ${formatStatus(tx.status)}`,
          amount: `${sign}${formatCurrency(amount, currency)}`,
          time: 'Registro manual',
          icon: transactionIcon(kind),
          tone: transactionTone(kind),
          kind,
        }
      }),
    }
  })
}

function transactionIcon(kind) {
  if (kind === 'expense') return 'shopping_bag'
  if (kind === 'income') return 'payments'
  if (kind === 'transfer') return 'swap_horiz'
  return 'receipt_long'
}

function transactionTone(kind) {
  if (kind === 'expense') return 'orange'
  if (kind === 'income') return 'green'
  if (kind === 'transfer') return 'blue'
  return 'slate'
}

function accountIcon(type) {
  if (type === 'bank') return 'account_balance'
  if (type === 'savings') return 'savings'
  if (type === 'investment') return 'query_stats'
  if (type === 'credit_card') return 'credit_card'
  if (type === 'digital_wallet') return 'account_balance_wallet'
  return 'payments'
}

function formatType(type = '') {
  const labels = {
    bank: 'Banco',
    savings: 'Ahorros',
    investment: 'Inversión',
    credit_card: 'Tarjeta de crédito',
    digital_wallet: 'Billetera digital',
    cash: 'Efectivo',
    expense: 'Gasto',
    income: 'Ingreso',
    transfer: 'Transferencia',
    recurring: 'Recurrente',
    pending: 'Pendiente',
    completed: 'Completada',
    cancelled: 'Cancelada',
    failed: 'Fallida',
  }
  if (labels[type]) {
    return labels[type]
  }
  return type
    .split('_')
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ')
}

function formatStatus(status = '') {
  const labels = {
    pending: 'Pendiente',
    confirmed: 'Confirmada',
    completed: 'Completada',
    cancelled: 'Cancelada',
    failed: 'Fallida',
  }
  return labels[status] || formatType(status)
}

function formatGroupDate(dateValue) {
  const date = new Date(`${dateValue}T00:00:00`)
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

function formatDayMonth(dateValue) {
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
  }).format(new Date(`${dateValue}T00:00:00`))
}

function formatShortDate(dateValue) {
  return new Intl.DateTimeFormat('es-ES', {
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${dateValue}T00:00:00`))
}

function formatCurrency(value, currency = 'COP') {
  const locale = currency === 'USD' ? 'en-US' : 'es-CO'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function formatSignedCurrency(value, currency = 'COP') {
  const numeric = Number(value || 0)
  if (numeric < 0) {
    return `-${formatCurrency(Math.abs(numeric), currency)}`
  }
  return formatCurrency(numeric, currency)
}

export default App
