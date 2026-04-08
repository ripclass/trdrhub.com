import { cn } from "@/lib/utils";

export interface SectionNavItem {
  id: string;
  label: string;
  count?: number;
  hidden?: boolean;
}

interface SectionNavProps {
  sections: SectionNavItem[];
  className?: string;
}

export function SectionNav({ sections, className }: SectionNavProps) {
  const visibleSections = sections.filter((s) => !s.hidden);

  if (visibleSections.length === 0) return null;

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <nav
      className={cn(
        "sticky top-0 z-10 flex items-center gap-1 rounded-lg border bg-card px-2 py-1.5 shadow-sm",
        className,
      )}
    >
      {visibleSections.map((section, idx) => (
        <button
          key={section.id}
          type="button"
          onClick={() => scrollToSection(section.id)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            "text-muted-foreground hover:text-foreground hover:bg-muted/50",
          )}
        >
          {section.label}
          {section.count != null && section.count > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium tabular-nums">
              {section.count}
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}
