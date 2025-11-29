import { Building2, Mail, Phone, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

export function TRDRFooter() {
  return (
    <footer className="bg-muted/50 border-t border-gray-200">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-gradient-primary p-2 rounded-lg">
                <Building2 className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">TRDR Hub</h3>
                <p className="text-xs text-muted-foreground">Transactional Risk & Data Reconciliation</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Everything Trade. One Platform. 15 tools for exporters, banks, and trade professionals.
            </p>
          </div>

          {/* Platform */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Tools</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/lcopilot" className="hover:text-foreground transition-colors">LCopilot <span className="text-xs text-primary">(Live)</span></Link></li>
              <li><Link to="/#tools" className="hover:text-foreground transition-colors">Sanctions Screener</Link></li>
              <li><Link to="/#tools" className="hover:text-foreground transition-colors">HS Code Calculator</Link></li>
              <li><Link to="/#tools" className="hover:text-foreground transition-colors">CustomsMate</Link></li>
              <li><Link to="/#tools" className="hover:text-foreground transition-colors">eBL Manager</Link></li>
              <li><Link to="/#tools" className="hover:text-foreground transition-colors text-xs opacity-70">+ 10 more tools</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Support</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/contact" className="hover:text-foreground transition-colors">Documentation</Link></li>
              <li><Link to="/contact" className="hover:text-foreground transition-colors">API Reference</Link></li>
              <li><Link to="/contact" className="hover:text-foreground transition-colors">Help Center</Link></li>
              <li><Link to="/about" className="hover:text-foreground transition-colors">About Us</Link></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Contact</h4>
            <div className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                <span>support@trdrhub.com</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                <span>+880 1700-000000</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                <span>Dhaka, Bangladesh</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-200">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-muted-foreground">
              © 2025 TRDR Hub. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <Link to="/pricing" className="hover:text-foreground transition-colors">Pricing</Link>
              <Link to="/contact" className="hover:text-foreground transition-colors">Contact</Link>
              <Link to="/about" className="hover:text-foreground transition-colors">About</Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}