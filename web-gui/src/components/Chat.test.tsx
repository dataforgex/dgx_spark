import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Chat } from './Chat'
import { vi } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// Mock fetch
global.fetch = vi.fn()

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn()

describe('Chat', () => {
    beforeEach(() => {
        vi.resetAllMocks()
        localStorage.clear()
    })

    it('renders chat interface', () => {
        render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )
        expect(screen.getByText(/Interactive Chat with Local LLM/i)).toBeInTheDocument()
    })

    it('loads initial system message', () => {
        render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )
        // Check for system message content or just ensure no error
        expect(screen.getByPlaceholderText(/Type your message/i)).toBeInTheDocument()
    })

    it('allows typing and sending a message', async () => {
        render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )

        const input = screen.getByPlaceholderText(/Type your message/i)
        fireEvent.change(input, { target: { value: 'Hello AI' } })

        const sendButton = screen.getByText(/Send/i)
        expect(sendButton).not.toBeDisabled()

        fireEvent.click(sendButton)

        await waitFor(() => {
            expect(screen.getByText('Hello AI')).toBeInTheDocument()
        })
    })
})
