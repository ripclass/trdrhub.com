import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { cn } from "@/lib/utils";

interface LegalLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalLayout({ title, lastUpdated, children }: LegalLayoutProps) {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-48 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-16 text-center">
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-6 font-display">
                {title}
              </h1>
              <p className="text-[#EDF5F2]/40 font-mono text-sm uppercase tracking-widest">
                Last Updated: {lastUpdated}
              </p>
            </div>

            {/* Content Card */}
            <div className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-3xl p-8 md:p-12 relative overflow-hidden backdrop-blur-sm">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
              
              <div className="relative z-10 prose prose-invert prose-lg max-w-none prose-headings:font-display prose-headings:text-white prose-p:text-[#EDF5F2]/80 prose-strong:text-white prose-a:text-[#B2F273] prose-li:text-[#EDF5F2]/80 hover:prose-a:text-[#a3e662]">
                {children}
              </div>
            </div>
          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
}
