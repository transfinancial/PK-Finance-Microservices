import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import BottomNav from './components/BottomNav'
import FundsView from './components/FundsView'
import StocksView from './components/StocksView'
import IndicesView from './components/IndicesView'
import { api } from './api'

export default function App() {
  const [tab, setTab] = useState('funds')
  const [health, setHealth] = useState(null)

  const checkHealth = useCallback(() => {
    api.health()
      .then(d => setHealth(d))
      .catch(() => setHealth(null))
  }, [])

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 60000)
    return () => clearInterval(id)
  }, [checkHealth])

  return (
    <div className="app">
      <Header health={health} />
      <main className="main-content">
        {tab === 'funds' && <FundsView />}
        {tab === 'stocks' && <StocksView />}
        {tab === 'indices' && <IndicesView />}
      </main>
      <BottomNav tab={tab} onChange={setTab} />
    </div>
  )
}
