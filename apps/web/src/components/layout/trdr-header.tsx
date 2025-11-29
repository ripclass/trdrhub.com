import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Home", href: "/" },
  { name: "Tools", href: "/tools" },
  { name: "Technology", href: "#technology" },
  { name: "Pricing", href: "/pricing" },
  { name: "About", href: "/about" },
];

export function TRDRHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-white">TRDR</span>
            <span className="text-xl font-bold text-blue-500">Hub</span>
          </Link>

          {/* Desktop navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className="text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login">
              <Button 
                variant="ghost" 
                size="sm" 
                className="text-slate-400 hover:text-white hover:bg-slate-800"
              >
                Login
              </Button>
            </Link>
            <Link to="/lcopilot">
              <Button 
                size="sm" 
                className="bg-white text-slate-900 hover:bg-slate-100 font-medium"
              >
                Get Started
              </Button>
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-slate-400 hover:text-white"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <div
        className={cn(
          "md:hidden absolute top-16 left-0 right-0 bg-slate-950 border-b border-slate-800 transition-all duration-300",
          mobileMenuOpen ? "opacity-100 visible" : "opacity-0 invisible"
        )}
      >
        <div className="container mx-auto px-4 py-4">
          <nav className="flex flex-col gap-2">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-900 rounded-lg transition-colors"
              >
                {item.name}
              </Link>
            ))}
            <div className="flex gap-2 mt-4 px-4">
              <Link to="/login" className="flex-1">
                <Button 
                  variant="outline" 
                  className="w-full border-slate-700 text-slate-300"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Button>
              </Link>
              <Link to="/lcopilot" className="flex-1">
                <Button 
                  className="w-full bg-white text-slate-900"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Get Started
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
