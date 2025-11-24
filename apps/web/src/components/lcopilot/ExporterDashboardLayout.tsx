import DashboardNav from "./DashboardNav";

type LayoutProps = {
  children: React.ReactNode;
};

export default function ExporterDashboardLayout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">TRDR Hub</p>
            <h1 className="text-xl font-semibold">Exporter LC Workspace</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div className="text-right">
              <p className="font-semibold">LCopilot SME Edition</p>
              <p>Global trade automation</p>
            </div>
            <div className="h-10 w-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold">
              LC
            </div>
          </div>
        </div>
      </header>
      <DashboardNav />
      <main className="mx-auto w-full max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}

