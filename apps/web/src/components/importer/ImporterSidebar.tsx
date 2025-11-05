import { Upload, FileText, History, Bell, BarChart3, Settings, HelpCircle } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from "@/components/ui/sidebar";

const navMain = [
  {
    title: "Upload LC",
    url: "/lcopilot/importer-dashboard?tab=upload",
    icon: Upload,
  },
  {
    title: "Processing Queue",
    url: "/lcopilot/importer-dashboard?tab=queue",
    icon: FileText,
  },
  {
    title: "Review Results",
    url: "/lcopilot/importer-dashboard?tab=results",
    icon: History,
  },
  {
    title: "Analytics",
    url: "/lcopilot/importer-dashboard?tab=analytics",
    icon: BarChart3,
  },
  {
    title: "Notifications",
    url: "/lcopilot/importer-dashboard?tab=notifications",
    icon: Bell,
  },
];

const navSecondary = [
  {
    title: "Settings",
    url: "/lcopilot/importer-dashboard?tab=settings",
    icon: Settings,
  },
  {
    title: "Help",
    url: "/help",
    icon: HelpCircle,
  },
];

export function ImporterSidebar() {
  return (
    <Sidebar>
      <SidebarContent>
        {/* Main Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Main Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navMain.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Secondary Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Support</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navSecondary.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="p-4 text-xs text-muted-foreground">
          <p className="font-medium">Importer Dashboard</p>
          <p>LC Review & Compliance</p>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
