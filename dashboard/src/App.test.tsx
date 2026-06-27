import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { axe } from 'jest-axe'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('App safety shell', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('offline'))),
    )
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('keeps paper mode, execution gate, and kill switch visible', async () => {
    render(<App />)

    expect(screen.getByText('paper')).toBeInTheDocument()
    expect(screen.getByText('gated')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Kill switch' })).toBeInTheDocument()
    expect(await screen.findByText(/API unavailable/)).toBeInTheDocument()
  })

  it('requires an explicit second kill-switch action', () => {
    render(<App />)

    const killSwitch = screen.getByRole('button', { name: 'Kill switch' })
    fireEvent.click(killSwitch)

    expect(screen.getByRole('button', { name: 'Confirm kill switch' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('calls the backend on confirmed kill-switch action', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/health')) {
        return Promise.resolve(Response.json({ mode: 'paper', execution_enabled: true }))
      }
      if (url.endsWith('/api/account/snapshot')) {
        return Promise.resolve(
          Response.json({ snapshot: { mode: 'paper', equity: 100000, cash: 90000 } }),
        )
      }
      if (url.endsWith('/api/risk/status')) {
        return Promise.resolve(Response.json({ risk: { cash_buffer_pct: 0.1 } }))
      }
      if (url.endsWith('/api/positions')) {
        return Promise.resolve(Response.json({ positions: [] }))
      }
      if (url.endsWith('/api/orders/open')) {
        return Promise.resolve(Response.json({ orders: [] }))
      }
      if (url.endsWith('/api/research/artifacts/latest')) {
        return Promise.resolve(Response.json({ artifacts: {}, missing: [] }))
      }
      if (url.endsWith('/api/system/kill-switch')) {
        return Promise.resolve(
          Response.json({
            mode: 'paper',
            execution_enabled: false,
            state: { mode: 'killed', reason: 'operator dashboard' },
          }),
        )
      }
      return Promise.reject(new Error(`unexpected request: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    const killSwitch = await screen.findByRole('button', { name: 'Kill switch' })
    fireEvent.click(killSwitch)
    fireEvent.click(screen.getByRole('button', { name: 'Confirm kill switch' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/system/kill-switch',
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('refreshes dashboard snapshots after initial load', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/health')) {
        return Promise.resolve(Response.json({ mode: 'paper', execution_enabled: true }))
      }
      if (url.endsWith('/api/account/snapshot')) {
        return Promise.resolve(
          Response.json({ snapshot: { mode: 'paper', equity: 100000, cash: 90000 } }),
        )
      }
      if (url.endsWith('/api/risk/status')) {
        return Promise.resolve(Response.json({ risk: { cash_buffer_pct: 0.1 } }))
      }
      if (url.endsWith('/api/positions')) {
        return Promise.resolve(Response.json({ positions: [] }))
      }
      if (url.endsWith('/api/orders/open')) {
        return Promise.resolve(Response.json({ orders: [] }))
      }
      if (url.endsWith('/api/research/artifacts/latest')) {
        return Promise.resolve(Response.json({ artifacts: {}, missing: [] }))
      }
      return Promise.reject(new Error(`unexpected request: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('paper linked')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(6)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(fetchMock).toHaveBeenCalledTimes(12)
  })

  it('renders backend research artifact candidates', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/health')) {
        return Promise.resolve(Response.json({ mode: 'paper', execution_enabled: false }))
      }
      if (url.endsWith('/api/account/snapshot')) {
        return Promise.resolve(
          Response.json({ snapshot: { mode: 'paper', equity: 100000, cash: 90000 } }),
        )
      }
      if (url.endsWith('/api/risk/status')) {
        return Promise.resolve(Response.json({ risk: { cash_buffer_pct: 0.1 } }))
      }
      if (url.endsWith('/api/positions')) {
        return Promise.resolve(Response.json({ positions: [] }))
      }
      if (url.endsWith('/api/orders/open')) {
        return Promise.resolve(Response.json({ orders: [] }))
      }
      if (url.endsWith('/api/research/artifacts/latest')) {
        return Promise.resolve(
          Response.json({
            artifacts: {
              consistent_trade_plan: {
                items: [
                  {
                    symbol: 'XLK',
                    strategy: 'swing_momentum_10_30',
                    score: 0.74,
                    test_sharpe: 1.76,
                  },
                ],
              },
              research_loop_summary: [{ iteration: '1', consistent_items: '1' }],
            },
            missing: [],
          }),
        )
      }
      return Promise.reject(new Error(`unexpected request: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: 'Research' }))

    expect(await screen.findByText('XLK')).toBeInTheDocument()
    expect(screen.getByText('swing_momentum_10_30')).toBeInTheDocument()
    expect(screen.getByText('1 consistent item')).toBeInTheDocument()
  })

  it('does not show mock candidates when backend artifacts are empty', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/health')) {
        return Promise.resolve(Response.json({ mode: 'paper', execution_enabled: false }))
      }
      if (url.endsWith('/api/account/snapshot')) {
        return Promise.resolve(
          Response.json({ snapshot: { mode: 'paper', equity: 100000, cash: 90000 } }),
        )
      }
      if (url.endsWith('/api/risk/status')) {
        return Promise.resolve(Response.json({ risk: { cash_buffer_pct: 0.1 } }))
      }
      if (url.endsWith('/api/positions')) {
        return Promise.resolve(Response.json({ positions: [] }))
      }
      if (url.endsWith('/api/orders/open')) {
        return Promise.resolve(Response.json({ orders: [] }))
      }
      if (url.endsWith('/api/research/artifacts/latest')) {
        return Promise.resolve(
          Response.json({
            artifacts: { consistent_trade_plan: { items: [] }, research_loop_summary: [] },
            missing: [],
          }),
        )
      }
      return Promise.reject(new Error(`unexpected request: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: 'Research' }))

    expect(await screen.findByText('No consistency-selected candidates')).toBeInTheDocument()
    expect(screen.queryByText('trend_sma_50_150')).not.toBeInTheDocument()
  })

  it('keeps core dashboard live when research artifacts fail to load', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/health')) {
        return Promise.resolve(Response.json({ mode: 'paper', execution_enabled: false }))
      }
      if (url.endsWith('/api/account/snapshot')) {
        return Promise.resolve(
          Response.json({ snapshot: { mode: 'paper', equity: 125000, cash: 90000 } }),
        )
      }
      if (url.endsWith('/api/risk/status')) {
        return Promise.resolve(Response.json({ risk: { cash_buffer_pct: 0.1 } }))
      }
      if (url.endsWith('/api/positions')) {
        return Promise.resolve(Response.json({ positions: [] }))
      }
      if (url.endsWith('/api/orders/open')) {
        return Promise.resolve(Response.json({ orders: [] }))
      }
      if (url.endsWith('/api/research/artifacts/latest')) {
        return Promise.resolve(Response.json({ detail: 'artifact read failed' }, { status: 500 }))
      }
      return Promise.reject(new Error(`unexpected request: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByText('paper linked')).toBeInTheDocument()
    expect(screen.queryByText(/API unavailable/)).not.toBeInTheDocument()
  })

  it('renders all five dashboard screens without hiding safety status', () => {
    render(<App />)

    for (const [tab, heading] of [
      ['Command', 'Paper equity'],
      ['Timeline', 'Agent Decision Timeline'],
      ['Research', 'Research Lab'],
      ['Risk', 'Risk Cockpit'],
      ['Settings', 'Settings + Integrations'],
    ]) {
      fireEvent.click(screen.getByRole('button', { name: tab }))
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
      expect(screen.getByText('paper')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /kill switch/i })).toBeInTheDocument()
    }
  })

  it('does not render raw credential markers', () => {
    const { container } = render(<App />)

    expect(container).not.toHaveTextContent(/sk_live|alpaca_secret|api key|private key/i)
  })

  it('has no automated accessibility violations in the safety shell', async () => {
    const { container } = render(<App />)

    const results = await axe(container)

    expect(results.violations).toEqual([])
  })
})