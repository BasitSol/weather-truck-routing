import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { AnalyzeRequest, AnalyzeResponse, ApiErrorBody, Place } from './types'

export class ApiError extends Error {
  readonly code: string
  readonly fields: Record<string, string[]>

  constructor(code: string, message: string, fields: Record<string, string[]> = {}) {
    super(message)
    this.code = code
    this.fields = fields
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError('network', 'The server could not be reached. Check your connection and try again.')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const err = (body as ApiErrorBody | null)?.error
    throw new ApiError(err?.code ?? 'http_error', err?.message ?? `Request failed (${response.status}).`, err?.fields)
  }
  return body as T
}

export function analyzeTrip(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request('/analyze', { method: 'POST', body: JSON.stringify(req) })
}

export function useAnalyze() {
  return useMutation<AnalyzeResponse, ApiError, AnalyzeRequest>({ mutationFn: analyzeTrip })
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms)
    return () => window.clearTimeout(id)
  }, [value, ms])
  return debounced
}

/** Place suggestions for typeahead: debounced, cached for the session, at least 3 characters. */
export function usePlaceSearch(text: string, bias: Pick<Place, 'lat' | 'lon'> | null) {
  const q = useDebounced(text.trim(), 250)
  const at = bias ? `${bias.lat.toFixed(2)},${bias.lon.toFixed(2)}` : ''
  return useQuery({
    queryKey: ['geocode', q.toLowerCase(), at],
    enabled: q.length >= 3,
    staleTime: Infinity,
    retry: false,
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ q, limit: '6' })
      if (at) params.set('at', at)
      return request<{ results: Place[] }>(`/geocode?${params}`, { signal }).then((r) => r.results)
    },
  })
}
