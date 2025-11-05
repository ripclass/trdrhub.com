import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import {
  Filter,
  X,
  Save,
  Trash2,
  Check,
  ChevronsUpDown,
} from "lucide-react";

// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}

import { BankResultsFilters } from "@/api/bank";

const DISCREPANCY_TYPES = [
  { value: "date_mismatch", label: "Date Mismatch" },
  { value: "amount_mismatch", label: "Amount Mismatch" },
  { value: "party_mismatch", label: "Party Mismatch" },
  { value: "port_mismatch", label: "Port Mismatch" },
  { value: "missing_field", label: "Missing Field" },
  { value: "invalid_format", label: "Invalid Format" },
] as const;

interface FilterPreset {
  id: string;
  name: string;
  filters: BankResultsFilters;
  createdAt: string;
}

interface AdvancedFiltersProps {
  filters: BankResultsFilters;
  onFiltersChange: (filters: BankResultsFilters) => void;
}

const PRESET_STORAGE_KEY = "bank-filter-presets";

export function AdvancedFilters({ filters, onFiltersChange }: AdvancedFiltersProps) {
  const [minScore, setMinScore] = useState<number>(filters.min_score ?? 0);
  const [maxScore, setMaxScore] = useState<number>(filters.max_score ?? 100);
  const [discrepancyType, setDiscrepancyType] = useState<string>(filters.discrepancy_type || "all");
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [presetName, setPresetName] = useState("");
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [presetOpen, setPresetOpen] = useState(false);

  // Load presets from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PRESET_STORAGE_KEY);
      if (saved) {
        setPresets(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to load filter presets:", e);
    }
  }, []);

  // Apply filters when they change (but not on initial mount to avoid infinite loop)
  const isInitialMount = useRef(true);
  
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    const newFilters: BankResultsFilters = {
      ...filters,
      min_score: minScore === 0 ? undefined : minScore,
      max_score: maxScore === 100 ? undefined : maxScore,
      discrepancy_type: discrepancyType === "all" ? undefined : discrepancyType as any,
    };
    
    // Remove undefined values
    Object.keys(newFilters).forEach((key) => {
      if (newFilters[key as keyof BankResultsFilters] === undefined) {
        delete newFilters[key as keyof BankResultsFilters];
      }
    });
    
    onFiltersChange(newFilters);
  }, [minScore, maxScore, discrepancyType]);

  const handleSavePreset = () => {
    if (!presetName.trim()) return;

    const preset: FilterPreset = {
      id: `preset-${Date.now()}`,
      name: presetName.trim(),
      filters: {
        ...filters,
        min_score: minScore === 0 ? undefined : minScore,
        max_score: maxScore === 100 ? undefined : maxScore,
        discrepancy_type: discrepancyType === "all" ? undefined : discrepancyType as any,
      },
      createdAt: new Date().toISOString(),
    };

    // Remove undefined values
    Object.keys(preset.filters).forEach((key) => {
      if (preset.filters[key as keyof BankResultsFilters] === undefined) {
        delete preset.filters[key as keyof BankResultsFilters];
      }
    });

    const updatedPresets = [...presets, preset];
    setPresets(updatedPresets);
    localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(updatedPresets));
    setPresetName("");
    setShowSavePreset(false);
  };

  const handleLoadPreset = (preset: FilterPreset) => {
    setMinScore(preset.filters.min_score ?? 0);
    setMaxScore(preset.filters.max_score ?? 100);
    setDiscrepancyType(preset.filters.discrepancy_type || "all");
    
    // Apply other filters from preset
    onFiltersChange(preset.filters);
    setPresetOpen(false);
  };

  const handleDeletePreset = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updatedPresets = presets.filter((p) => p.id !== id);
    setPresets(updatedPresets);
    localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(updatedPresets));
  };

  const handleClearFilters = () => {
    setMinScore(0);
    setMaxScore(100);
    setDiscrepancyType("all");
    onFiltersChange({});
  };

  const hasActiveFilters = 
    minScore > 0 || 
    maxScore < 100 || 
    discrepancyType !== "all";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Advanced Filters
            </CardTitle>
            <CardDescription>
              Filter results by compliance score and discrepancy type
            </CardDescription>
          </div>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              <X className="w-4 h-4 mr-2" />
              Clear All
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Compliance Score Range */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Compliance Score Range</Label>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{minScore}%</Badge>
              <span className="text-muted-foreground">to</span>
              <Badge variant="outline">{maxScore}%</Badge>
            </div>
          </div>
          <div className="space-y-2">
            <Slider
              value={[minScore, maxScore]}
              onValueChange={(values) => {
                setMinScore(values[0]);
                setMaxScore(values[1]);
              }}
              min={0}
              max={100}
              step={1}
              className="w-full"
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        {/* Discrepancy Type */}
        <div className="space-y-2">
          <Label>Discrepancy Type</Label>
          <Select value={discrepancyType} onValueChange={setDiscrepancyType}>
            <SelectTrigger>
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {DISCREPANCY_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Saved Presets */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Saved Filter Presets</Label>
            <Popover open={presetOpen} onOpenChange={setPresetOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm">
                  <Save className="w-4 h-4 mr-2" />
                  Manage Presets
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0" align="end">
                <Command>
                  <CommandInput placeholder="Search presets..." />
                  <CommandList>
                    <CommandEmpty>No presets saved</CommandEmpty>
                    <CommandGroup>
                      {presets.map((preset) => (
                        <CommandItem
                          key={preset.id}
                          value={preset.name}
                          onSelect={() => handleLoadPreset(preset)}
                          className="flex items-center justify-between"
                        >
                          <div className="flex items-center gap-2">
                            <Check className={cn("h-4 w-4", "opacity-0")} />
                            <span>{preset.name}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleDeletePreset(preset.id, e)}
                            className="h-6 w-6 p-0"
                          >
                            <Trash2 className="h-3 w-3 text-destructive" />
                          </Button>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
                <div className="border-t p-2">
                  {showSavePreset ? (
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder="Preset name..."
                        value={presetName}
                        onChange={(e) => setPresetName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleSavePreset();
                          } else if (e.key === "Escape") {
                            setShowSavePreset(false);
                            setPresetName("");
                          }
                        }}
                        className="flex-1"
                        autoFocus
                      />
                      <Button size="sm" onClick={handleSavePreset}>
                        Save
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setShowSavePreset(false);
                          setPresetName("");
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => setShowSavePreset(true)}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      Save Current Filters as Preset
                    </Button>
                  )}
                </div>
              </PopoverContent>
            </Popover>
          </div>
          {presets.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {presets.map((preset) => (
                <Badge
                  key={preset.id}
                  variant="secondary"
                  className="cursor-pointer hover:bg-secondary/80"
                  onClick={() => handleLoadPreset(preset)}
                >
                  {preset.name}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

