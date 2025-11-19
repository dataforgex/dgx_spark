import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
  type ScriptableContext
} from 'chart.js'
import { Line, Doughnut } from 'react-chartjs-2'
import './Dashboard.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
)

interface GPUMetrics {
  index: number
  name: string
  temperature: number
  powerDraw: number
  powerLimit: number
  memoryUsed: number
  memoryTotal: number
  utilizationGpu: number
}

interface SystemMetrics {
  gpus: GPUMetrics[]
  memoryUsed: number
  memoryTotal: number
  cpuUsage: number
  timestamp: number
}

interface ModelStatus {
  name: string
  port: number
  healthy: boolean
  responseTime: number | null
}

interface DockerContainer {
  name: string
  status: string
  ports: string
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  // Keep up to 1 hour of history (720 points at 5s interval)
  const MAX_HISTORY_POINTS = 720
  const [history, setHistory] = useState<SystemMetrics[]>(() => {
    const saved = localStorage.getItem('dashboard_history')
    return saved ? JSON.parse(saved) : []
  })
  const [modelStatus, setModelStatus] = useState<ModelStatus[]>([])
  const [containers, setContainers] = useState<DockerContainer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Use the current hostname instead of hardcoded localhost
  const API_BASE = `http://${window.location.hostname}:5174`

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/metrics`)
        if (!response.ok) throw new Error('Failed to fetch metrics')
        const data: SystemMetrics = await response.json()
        setMetrics(data)
        setHistory(prev => {
          const newHistory = [...prev, data].slice(-MAX_HISTORY_POINTS)
          localStorage.setItem('dashboard_history', JSON.stringify(newHistory))
          return newHistory
        })
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }

    const fetchModelStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/models`)
        if (!response.ok) throw new Error('Failed to fetch model status')
        const data: ModelStatus[] = await response.json()
        setModelStatus(data)
      } catch (err) {
        console.error('Failed to fetch model status:', err)
      }
    }

    const fetchContainers = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/containers`)
        if (!response.ok) throw new Error('Failed to fetch containers')
        const data: DockerContainer[] = await response.json()
        setContainers(data)
      } catch (err) {
        console.error('Failed to fetch containers:', err)
      }
    }

    fetchMetrics()
    fetchModelStatus()
    fetchContainers()
    setLoading(false)

    const interval = setInterval(() => {
      fetchMetrics()
      fetchModelStatus()
      fetchContainers()
    }, 5000)

    return () => clearInterval(interval)
  }, [API_BASE])

  if (loading) {
    return <div className="dashboard-loading">Loading dashboard...</div>
  }

  if (error && !metrics) {
    return (
      <div className="dashboard-error">
        <h2>Connection Error</h2>
        <p>{error}</p>
        <p>Make sure the metrics API server is running on port 5174</p>
      </div>
    )
  }

  const memoryData = metrics
    ? {
      labels: ['Used', 'Free'],
      datasets: [
        {
          data: [metrics.memoryUsed, metrics.memoryTotal - metrics.memoryUsed],
          backgroundColor: ['rgba(59, 130, 246, 0.8)', 'rgba(30, 41, 59, 0.5)'], // Blue 500, Slate 800
          borderColor: ['rgba(59, 130, 246, 1)', 'rgba(30, 41, 59, 1)'],
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    }
    : null

  const gpuUtilizationHistory = {
    labels: history.map((_, i) => `${i * 5}s`),
    datasets:
      metrics?.gpus.map((gpu, idx) => ({
        label: `GPU ${gpu.index}`,
        data: history.map(h => h.gpus[idx]?.utilizationGpu || 0),
        borderColor: idx === 0 ? '#3b82f6' : '#6366f1', // Blue 500 or Indigo 500
        backgroundColor: (context: ScriptableContext<'line'>) => {
          const ctx = context.chart.ctx
          const gradient = ctx.createLinearGradient(0, 0, 0, 200)
          gradient.addColorStop(0, idx === 0 ? 'rgba(59, 130, 246, 0.5)' : 'rgba(99, 102, 241, 0.5)')
          gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)')
          return gradient
        },
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
      })) || [],
  }

  const temperatureHistory = {
    labels: history.map((_, i) => `${i * 5}s`),
    datasets:
      metrics?.gpus.map((gpu, idx) => ({
        label: `GPU ${gpu.index} Temp`,
        data: history.map(h => h.gpus[idx]?.temperature || 0),
        borderColor: '#f59e0b', // Amber 500
        backgroundColor: (context: ScriptableContext<'line'>) => {
          const ctx = context.chart.ctx
          const gradient = ctx.createLinearGradient(0, 0, 0, 200)
          gradient.addColorStop(0, 'rgba(245, 158, 11, 0.5)')
          gradient.addColorStop(1, 'rgba(245, 158, 11, 0.0)')
          return gradient
        },
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
      })) || [],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#94a3b8', // Slate 400
          font: {
            family: "'Inter', sans-serif",
            size: 12,
          },
          usePointStyle: true,
          boxWidth: 8,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)', // Slate 900
        titleColor: '#f8fafc', // Slate 50
        bodyColor: '#cbd5e1', // Slate 300
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#64748b', // Slate 500
          font: { size: 10 },
        },
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
      },
      y: {
        ticks: {
          color: '#64748b', // Slate 500
          font: { size: 10 },
        },
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
        beginAtZero: true,
      },
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
  }

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        <div className="dashboard-header">
          <h1>DGX Spark Monitoring</h1>
          <div className="status-badge">
            {error ? '⚠️ Connection Issues' : '✓ System Online'}
          </div>
        </div>

        {/* System Memory */}
        <div className="dashboard-row">
          <div className="card full">
            <h2>System Resources</h2>
            <div className="chart-group">
              <div className="chart-half">
                {memoryData && (
                  <div className="chart-container-small">
                    <Doughnut
                      data={memoryData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '70%',
                        plugins: {
                          legend: {
                            position: 'right',
                            labels: {
                              color: '#94a3b8',
                              usePointStyle: true,
                              boxWidth: 8,
                            },
                          },
                        },
                      }}
                    />
                  </div>
                )}
              </div>
              <div className="chart-half">
                <div className="metric-display">
                  <div className="metric-label">Memory Usage</div>
                  <div className="metric-value">
                    {metrics ? ((metrics.memoryUsed / metrics.memoryTotal) * 100).toFixed(1) : 0}%
                  </div>
                  <div className="metric-label">Used / Total</div>
                  <div className="metric-value">
                    {metrics ? metrics.memoryUsed.toFixed(1) : 0} <span style={{ fontSize: '1rem', color: 'var(--text-tertiary)' }}>/ {metrics ? metrics.memoryTotal.toFixed(1) : 0} GB</span>
                  </div>
                  <div className="metric-label">CPU Usage</div>
                  <div className="metric-value">
                    {metrics ? metrics.cpuUsage.toFixed(1) : 0}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* GPU Utilization */}
        <div className="dashboard-row">
          <div className="card half">
            <h2>GPU Utilization</h2>
            <div className="chart-container">
              <Line data={gpuUtilizationHistory} options={chartOptions} />
            </div>
            <div className="power-info">
              {metrics?.gpus.map(gpu => (
                <div key={gpu.index}>
                  GPU {gpu.index} Power: <span style={{ color: 'var(--text-primary)' }}>{gpu.powerDraw.toFixed(0)}W</span> / {gpu.powerLimit.toFixed(0)}W
                </div>
              ))}
            </div>
          </div>

          <div className="card half">
            <h2>GPU Temperature</h2>
            <div className="chart-container">
              <Line data={temperatureHistory} options={chartOptions} />
            </div>
          </div>
        </div>

        {/* vLLM Model Status */}
        <div className="dashboard-row">
          <div className="card full">
            <h2>vLLM Model Servers</h2>
            <div className="model-status-grid">
              {modelStatus.map(model => (
                <div key={model.port} className="model-card">
                  <div className="model-name">{model.name}</div>
                  <div className={`model-health ${model.healthy ? 'healthy' : 'unhealthy'}`}>
                    {model.healthy ? '✓ Online' : '✗ Offline'}
                  </div>
                  <div className="model-info">
                    <span>Port:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{model.port}</span>
                  </div>
                  {model.responseTime && (
                    <div className="model-info">
                      <span>Response:</span>
                      <span style={{ color: 'var(--text-primary)' }}>{model.responseTime}ms</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Docker Containers */}
        <div className="dashboard-row">
          <div className="card full">
            <h2>Docker Containers</h2>
            <table className="container-table">
              <thead>
                <tr>
                  <th>Container Name</th>
                  <th>Status</th>
                  <th>Ports</th>
                </tr>
              </thead>
              <tbody>
                {containers.map(container => (
                  <tr key={container.name}>
                    <td>{container.name}</td>
                    <td>
                      <span
                        className={`status-badge ${container.status.includes('Up') ? 'running' : 'stopped'
                          }`}
                      >
                        {container.status}
                      </span>
                    </td>
                    <td>{container.ports || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
