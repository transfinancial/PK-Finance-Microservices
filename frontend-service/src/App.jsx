import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import BottomNav from './components/BottomNav'
import SideNav from './components/SideNav'
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
      <div className="app-body">
        <SideNav tab={tab} onChange={setTab} />
        <main className="main-content">
          <div style={{ display: tab === 'funds' ? 'block' : 'none' }}><FundsView /></div>
          <div style={{ display: tab === 'stocks' ? 'block' : 'none' }}><StocksView /></div>
          <div style={{ display: tab === 'indices' ? 'block' : 'none' }}><IndicesView /></div>
        </main>
      </div>
      <BottomNav tab={tab} onChange={setTab} />
    </div>
  )
}
