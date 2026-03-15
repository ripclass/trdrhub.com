import { FileCheck, Loader2 } from 'lucide-react'

export default function LcopilotRouter() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/10 mb-6">
          <FileCheck className="w-8 h-8 text-blue-400" />
        </div>
        <div className="flex items-center justify-center gap-3 mb-4">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          <span className="text-lg text-white">Loading your dashboard...</span>
        </div>
        <p className="text-sm text-slate-400">Please wait...</p>
      </div>
    </div>
  )
}
