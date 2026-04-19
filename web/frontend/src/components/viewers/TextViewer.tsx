import { useQuery } from '@tanstack/react-query'
import { fileUrl } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

export default function TextViewer({ jobId, filename }: { jobId: string; filename: string }) {
  const url   = fileUrl(jobId, filename)
  const token = useAuthStore((s) => s.token)

  const { data, isLoading, isError } = useQuery<string>({
    queryKey: ['text', jobId, filename],
    queryFn:  async () => {
      const resp = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) throw new Error('Failed to fetch file')
      return resp.text()
    },
  })

  if (isLoading) return <p className="text-xs text-gray-500 animate-pulse">Loading…</p>
  if (isError)   return <p className="text-xs text-red-400">Failed to load file.</p>

  return (
    <pre className="text-xs text-gray-300 bg-gray-950 rounded-lg p-4 max-h-96 overflow-auto
                    font-mono whitespace-pre-wrap break-words leading-relaxed border border-gray-800">
      {data}
    </pre>
  )
}
