import { render, screen, waitFor } from '@testing-library/react'
import { Dashboard } from './Dashboard'
import { vi } from 'vitest'

// Mock fetch
global.fetch = vi.fn()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function createFetchResponse(data: any) {
    return { ok: true, json: () => Promise.resolve(data) }
}

describe('Dashboard', () => {
    beforeEach(() => {
        vi.resetAllMocks()
    })

    it('renders loading state initially', () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValue(createFetchResponse({}))
        render(<Dashboard />)
        expect(screen.getByText(/Loading dashboard/i)).toBeInTheDocument()
    })

    it('renders dashboard content after loading', async () => {
        const mockMetrics = {
            gpus: [],
            memoryUsed: 8,
            memoryTotal: 16,
            cpuUsage: 25,
            timestamp: Date.now()
        }

        const mockModels = [
            { name: 'Model A', port: 8000, healthy: true, responseTime: 50 }
        ]

        const mockContainers = [
            { name: 'container-1', status: 'Up', ports: '8000' }
        ]

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any)
                .mockResolvedValueOnce(createFetchResponse(mockMetrics))
                .mockResolvedValueOnce(createFetchResponse(mockModels))
                .mockResolvedValueOnce(createFetchResponse(mockContainers))

        render(<Dashboard />)

        await waitFor(() => {
            expect(screen.getByText(/DGX Spark Monitoring/i)).toBeInTheDocument()
        })

        expect(screen.getByText(/System Resources/i)).toBeInTheDocument()
    })
})
