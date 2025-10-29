import { Button } from "@/components/ui/button";
import { FileText, Menu, User } from "lucide-react";

export function Header() {
  return (
    <header className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-primary p-2 rounded-lg">
              <FileText className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground">LCopilot</h1>
              <p className="text-xs text-muted-foreground">Document Validator</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6">
            <a href="/#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Features
            </a>
            <a href="/pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Pricing
            </a>
            <a href="/support" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Support
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <a href="/login">
              <Button variant="outline" size="sm" className="hidden sm:inline-flex">
                <User className="w-4 h-4 mr-2" />
                Login
              </Button>
            </a>
            <a href="/register">
              <Button size="sm" className="bg-gradient-primary hover:opacity-90">
                Get Started
              </Button>
            </a>
            <Button variant="outline" size="sm" className="md:hidden">
              <Menu className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}