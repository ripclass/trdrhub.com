import { Button } from "@/components/ui/button";
import { Menu, X, User, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const navigation = [
  { name: "Home", href: "/" },
  { name: "Tools", href: "/tools" },
  { name: "Technology", href: "/technology" },
  { name: "Pricing", href: "/pricing" },
  { name: "About", href: "/about" },
];

export function TRDRHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isLoading } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#00261C]/80 backdrop-blur-md border-b border-[#EDF5F2]/10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <img 
              src="/logo-dark-v2.png" 
              alt="TRDR Hub" 
              className="h-8 w-auto object-contain"
            />
          </Link>

          {/* Desktop navigation */}
          <nav className="hidden md:flex items-center gap-10">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className="text-xs font-mono font-medium tracking-widest uppercase text-[#EDF5F2]/70 hover:text-[#B2F273] transition-colors"
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Desktop CTAs - Show different buttons based on auth state */}
          <div className="hidden md:flex items-center gap-3">
            {!isLoading && user ? (
              // Logged in user
              <>
                <Link to="/hub">
                  <Button 
                    size="sm" 
                    className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-medium border-none font-mono uppercase tracking-wider text-xs"
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Go to Hub
                  </Button>
                </Link>
                <Link to="/hub">
                  <Avatar className="h-8 w-8 cursor-pointer border border-[#EDF5F2]/20">
                    <AvatarFallback className="bg-[#00382E] text-[#B2F273] text-sm">
                      {(user.full_name || user.email || "U").charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Link>
              </>
            ) : (
              // Not logged in
              <>
                <Link to="/login">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-[#EDF5F2]/60 hover:text-[#B2F273] hover:bg-[#00382E] font-mono uppercase tracking-wider text-xs"
                  >
                    Login
                  </Button>
                </Link>
                <Link to="/lcopilot">
                  <Button 
                    size="sm" 
                    className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-medium border-none font-mono uppercase tracking-wider text-xs"
                  >
                    Get Started
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-[#EDF5F2]/60 hover:text-[#B2F273]"
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
          "md:hidden absolute top-16 left-0 right-0 bg-[#00261C] border-b border-[#EDF5F2]/10 transition-all duration-300",
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
                className="px-4 py-3 text-xs font-mono font-medium tracking-widest uppercase text-[#EDF5F2]/70 hover:text-[#B2F273] hover:bg-[#00382E] rounded-lg transition-colors"
              >
                {item.name}
              </Link>
            ))}
            <div className="flex gap-2 mt-4 px-4">
              {!isLoading && user ? (
                // Logged in user - mobile
                <Link to="/hub" className="flex-1">
                  <Button 
                    className="w-full bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-mono uppercase tracking-wider text-xs"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Go to Hub
                  </Button>
                </Link>
              ) : (
                // Not logged in - mobile
                <>
                  <Link to="/login" className="flex-1">
                    <Button 
                      variant="outline" 
                      className="w-full border-[#EDF5F2]/20 text-[#EDF5F2]/60 hover:bg-[#00382E] hover:text-[#B2F273] bg-transparent font-mono uppercase tracking-wider text-xs"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Login
                    </Button>
                  </Link>
                  <Link to="/lcopilot" className="flex-1">
                    <Button 
                      className="w-full bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-mono uppercase tracking-wider text-xs"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Get Started
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
