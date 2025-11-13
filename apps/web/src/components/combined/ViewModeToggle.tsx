import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useCombined, type ViewMode } from "@/hooks/use-combined";
import { FileText, Package, Layers } from "lucide-react";

interface ViewModeToggleProps {
  disabled?: boolean;
  showAll?: boolean; // Whether to show "All" option
}

export function ViewModeToggle({ disabled = false, showAll = true }: ViewModeToggleProps) {
  const { viewMode, setViewMode } = useCombined();

  const handleValueChange = (value: string) => {
    if (value && (value === "export" || value === "import" || value === "all")) {
      setViewMode(value as ViewMode);
    }
  };

  return (
    <div className="flex items-center gap-2" role="group" aria-label="View mode selector">
      <ToggleGroup
        type="single"
        value={viewMode}
        onValueChange={handleValueChange}
        disabled={disabled}
        className="bg-muted/50 rounded-md p-1"
        aria-label="Select view mode"
      >
        {showAll && (
          <ToggleGroupItem 
            value="all" 
            aria-label="Show all export and import sessions" 
            className="data-[state=on]:bg-background"
            title="Show all sessions"
          >
            <Layers className="h-4 w-4 mr-2" aria-hidden="true" />
            <span>All</span>
          </ToggleGroupItem>
        )}
        <ToggleGroupItem 
          value="export" 
          aria-label="Show export sessions only" 
          className="data-[state=on]:bg-background"
          title="Export view"
        >
          <FileText className="h-4 w-4 mr-2" aria-hidden="true" />
          <span>Export</span>
        </ToggleGroupItem>
        <ToggleGroupItem 
          value="import" 
          aria-label="Show import sessions only" 
          className="data-[state=on]:bg-background"
          title="Import view"
        >
          <Package className="h-4 w-4 mr-2" aria-hidden="true" />
          <span>Import</span>
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}

