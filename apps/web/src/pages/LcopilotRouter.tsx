import { FileCheck, Loader2 } from 'lucide-react'

export default function LcopilotRouter() {
  return (
    <div className="min-h-screen bg-[#00261C] flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#B2F273]/10 mb-6">
          <FileCheck className="w-8 h-8 text-[#B2F273]" />
        </div>
        <div className="flex items-center justify-center gap-3 mb-4">
          <Loader2 className="w-5 h-5 text-[#B2F273] animate-spin" />
          <span className="text-lg text-white">Loading your dashboard...</span>
        </div>
        <p className="text-sm text-[#EDF5F2]/60">Please wait...</p>
      </div>
    </div>
  )
}
