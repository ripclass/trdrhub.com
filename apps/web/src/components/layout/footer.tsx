import { FileText, Mail, Phone, MapPin } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-foreground text-background py-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-primary p-2 rounded-lg">
                <FileText className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-bold">LCopilot</h3>
                <p className="text-sm text-background/70">Document Validator</p>
              </div>
            </div>
            <p className="text-background/80 text-sm leading-relaxed">
              Empowering Bangladeshi exporters with AI-powered LC document validation. 
              Fast, accurate, and compliant with international banking standards.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Platform</h4>
            <ul className="space-y-3 text-sm text-background/80">
              <li><a href="#" className="hover:text-primary transition-colors">Document Validation</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">OCR Processing</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">Compliance Check</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">API Access</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Support</h4>
            <ul className="space-y-3 text-sm text-background/80">
              <li><a href="#" className="hover:text-primary transition-colors">Documentation</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">Help Center</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">Contact Support</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">Status Page</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Contact</h4>
            <div className="space-y-3 text-sm text-background/80">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                <span>support@lcchecker.bd</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                <span>+880-1XXX-XXXXXX</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                <span>Dhaka, Bangladesh</span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-background/20 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-background/60">
              © 2024 LCopilot. All rights reserved. Built for Bangladeshi exporters.
            </p>
            <div className="flex gap-6 text-sm text-background/60">
              <a href="#" className="hover:text-primary transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-primary transition-colors">Terms of Service</a>
              <a href="#" className="hover:text-primary transition-colors">Cookie Policy</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}