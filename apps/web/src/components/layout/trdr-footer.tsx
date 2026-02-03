import { Link } from "react-router-dom";

const navigation = {
  product: [
    { name: "LCopilot", href: "/lcopilot" },
    { name: "Sanctions Screener", href: "/sanctions" },
    { name: "HS Code Finder", href: "/hs-code" },
    { name: "All Tools", href: "/tools" },
    { name: "Pricing", href: "/pricing" },
  ],
  resources: [
    { name: "Documentation", href: "/docs" },
    { name: "API Reference", href: "/api" },
    { name: "UCP600 Guide", href: "/guides/ucp600" },
    { name: "Blog", href: "/blog" },
  ],
  company: [
    { name: "About", href: "/about" },
    { name: "Contact", href: "/contact" },
    { name: "Careers", href: "/careers" },
  ],
  legal: [
    { name: "Privacy Policy", href: "/privacy" },
    { name: "Terms of Service", href: "/terms" },
    { name: "Security", href: "/security" },
  ],
};

export function TRDRFooter() {
  return (
    <footer className="bg-[#00261C] border-t border-[#EDF5F2]/10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="inline-block mb-4">
              <img 
                src="/logo-dark-v2.png" 
                alt="TRDR Hub" 
                className="h-10 w-auto object-contain"
              />
            </Link>
            <p className="text-[#EDF5F2]/60 text-sm mb-4">
              Zero-Error Trade Documents
            </p>
            <div className="text-[#EDF5F2]/40 text-sm">
              <a href="mailto:hello@trdrhub.com" className="hover:text-[#B2F273] transition-colors">
                hello@trdrhub.com
              </a>
            </div>
          </div>

          {/* Navigation columns */}
          <div>
            <h3 className="text-[#B2F273] font-semibold mb-4 font-display">Product</h3>
            <ul className="space-y-3">
              {navigation.product.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-[#EDF5F2]/60 hover:text-white transition-colors text-xs font-mono uppercase tracking-wider"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-[#B2F273] font-semibold mb-4 font-display">Resources</h3>
            <ul className="space-y-3">
              {navigation.resources.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-[#EDF5F2]/60 hover:text-white transition-colors text-xs font-mono uppercase tracking-wider"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-[#B2F273] font-semibold mb-4 font-display">Company</h3>
            <ul className="space-y-3">
              {navigation.company.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-[#EDF5F2]/60 hover:text-white transition-colors text-xs font-mono uppercase tracking-wider"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-[#B2F273] font-semibold mb-4 font-display">Legal</h3>
            <ul className="space-y-3">
              {navigation.legal.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-[#EDF5F2]/60 hover:text-white transition-colors text-xs font-mono uppercase tracking-wider"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-[#EDF5F2]/10 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-[#EDF5F2]/40 text-sm">
            © 2025 TRDR Hub. All rights reserved.
          </p>
          
          {/* Social links */}
          <div className="flex items-center gap-6">
            <a
              href="https://linkedin.com/company/trdrhub"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#EDF5F2]/40 hover:text-[#B2F273] transition-colors"
            >
              <span className="sr-only">LinkedIn</span>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
            </a>
            <a
              href="https://twitter.com/trdrhub"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#EDF5F2]/40 hover:text-[#B2F273] transition-colors"
            >
              <span className="sr-only">Twitter</span>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
