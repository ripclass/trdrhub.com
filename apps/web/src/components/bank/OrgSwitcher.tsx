/**
 * OrgSwitcher Component
 * Dropdown for switching between bank organizations
 */
import * as React from "react";
import { Building2, ChevronDown, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useOrgContext, BankOrg } from "@/contexts/OrgContext";
import { cn } from "@/lib/utils";

export function OrgSwitcher() {
  const { activeOrgId, setActiveOrg, orgs, isLoading } = useOrgContext();
  const [open, setOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");
  
  const activeOrg = orgs.find((o) => o.id === activeOrgId);
  
  const filteredOrgs = React.useMemo(() => {
    if (!searchQuery) return orgs;
    const query = searchQuery.toLowerCase();
    return orgs.filter(
      (org) =>
        org.name.toLowerCase().includes(query) ||
        org.code?.toLowerCase().includes(query)
    );
  }, [orgs, searchQuery]);
  
  const handleSelectOrg = (orgId: string | null) => {
    setActiveOrg(orgId);
    setOpen(false);
    setSearchQuery("");
  };
  
  if (isLoading) {
    return (
      <Button variant="outline" size="sm" disabled>
        <Building2 className="h-4 w-4 mr-2" />
        Loading...
      </Button>
    );
  }
  
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Building2 className="h-4 w-4" />
          <span className="max-w-[120px] truncate">
            {activeOrg ? activeOrg.name : "All Orgs"}
          </span>
          {activeOrg && (
            <Badge variant="secondary" className="text-xs">
              {activeOrg.kind}
            </Badge>
          )}
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <div className="p-3 border-b">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search orgs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>
        <ScrollArea className="h-[300px]">
          <div className="p-1">
            <button
              onClick={() => handleSelectOrg(null)}
              className={cn(
                "w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors",
                !activeOrgId && "bg-accent"
              )}
            >
              <div className="font-medium">All Orgs</div>
              <div className="text-xs text-muted-foreground">
                View all organizations
              </div>
            </button>
            {filteredOrgs.map((org) => (
              <button
                key={org.id}
                onClick={() => handleSelectOrg(org.id)}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors",
                  activeOrgId === org.id && "bg-accent"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{org.name}</span>
                  <Badge variant="outline" className="text-xs">
                    {org.kind}
                  </Badge>
                </div>
                {org.code && (
                  <div className="text-xs text-muted-foreground">{org.code}</div>
                )}
              </button>
            ))}
            {filteredOrgs.length === 0 && (
              <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                No organizations found
              </div>
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

