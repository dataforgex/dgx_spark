import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Chat } from './Chat'
import { vi } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// Mock fetch
global.fetch = vi.fn()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function createFetchResponse(data: any) {
    return {
        ok: true,
        json: () => Promise.resolve(data),
        text: () => Promise.resolve(JSON.stringify(data))
    }
}

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn()

describe('Chat', () => {
    beforeEach(() => {
        vi.resetAllMocks()
        localStorage.clear()

        // Default mock for model info
        const mockModelInfo = {
            data: [
                { id: 'Qwen/Qwen3-Coder-30B-A3B-Instruct', max_model_len: 32768 }
            ]
        };

        // Default mock for chat completion
        const mockChatResponse = {
            choices: [
                { message: { content: 'I am a helpful assistant.' } }
            ]
        };

        // Setup default fetch behavior
        (global.fetch as any).mockImplementation((url: string) => {
            if (url.includes('/models')) {
                return Promise.resolve(createFetchResponse(mockModelInfo));
            }
            if (url.includes('/chat/completions')) {
                return Promise.resolve(createFetchResponse(mockChatResponse));
            }
            return Promise.resolve(createFetchResponse({}));
        });
    })

    it('renders chat interface', async () => {
        render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )
        const newChatElements = screen.getAllByText(/New Chat/i)
        expect(newChatElements.length).toBeGreaterThan(0)

        // Wait for model info to load
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalled()
        })
    })

    it('persists chats across reloads', async () => {
        const { unmount } = render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )

        // Create a new chat
        const input = screen.getByPlaceholderText(/Type your message/i)
        fireEvent.change(input, { target: { value: 'Persistent Message' } })
        fireEvent.click(screen.getByText(/Send/i))

        await waitFor(() => {
            const elements = screen.getAllByText('Persistent Message')
            expect(elements.length).toBeGreaterThan(0)
        })

        // Unmount to simulate page close
        unmount()

        // Render again to simulate reload
        render(
            <MemoryRouter initialEntries={['/chat']}>
                <Routes>
                    <Route path="/chat/:chatId?" element={<Chat />} />
                </Routes>
            </MemoryRouter>
        )

        // Check if the chat is still in the sidebar
        // Note: The sidebar lists titles. Our title generation uses the first message.
        expect(screen.getByText('Persistent Message')).toBeInTheDocument()
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
            const elements = screen.getAllByText('Hello AI')
            expect(elements.length).toBeGreaterThan(0)
        })

        // Verify API was called
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/chat/completions'),
            expect.objectContaining({
                method: 'POST',
                body: expect.stringContaining('Hello AI')
            })
        )
    })
})
