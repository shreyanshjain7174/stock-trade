import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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