import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDate(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'active':
    case 'healthy':
    case 'running':
    case 'started':
      return 'text-emerald-400 bg-emerald-500/10'
    case 'inactive':
    case 'stopped':
      return 'text-gray-400 bg-gray-500/10'
    case 'error':
    case 'unhealthy':
    case 'crash':
      return 'text-red-400 bg-red-500/10'
    case 'loading':
      return 'text-yellow-400 bg-yellow-500/10'
    default:
      return 'text-gray-400 bg-gray-500/10'
  }
}

export function getStatusDot(status: string): string {
  switch (status.toLowerCase()) {
    case 'active':
    case 'healthy':
    case 'running':
    case 'started':
      return 'bg-emerald-500'
    case 'inactive':
    case 'stopped':
      return 'bg-gray-500'
    case 'error':
    case 'unhealthy':
      return 'bg-red-500'
    case 'loading':
      return 'bg-yellow-500 animate-pulse'
    default:
      return 'bg-gray-500'
  }
}

export const API_BASE = '/api/v1'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: optionHeaders, ...restOptions } = options || {}
  const response = await fetch(`${API_BASE}${path}`, {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      ...optionHeaders,
    } as Record<string, string>,
  })
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`API error: ${response.status} ${response.statusText}${text ? ` — ${text.slice(0, 300)}` : ''}`)
  }
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  // Non-JSON response — return as text wrapped in object
  const text = await response.text()
  return { text, status: response.status } as unknown as T
}
