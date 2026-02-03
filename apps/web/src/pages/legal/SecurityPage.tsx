import { LegalLayout } from "./LegalLayout";
import { Shield, Lock, Server, FileCheck } from "lucide-react";

const SecurityPage = () => {
  return (
    <LegalLayout title="Security & Compliance" lastUpdated="January 15, 2026">
      <p className="lead text-xl">
        Trust is the currency of trade. We've built TRDR Hub with a security-first architecture to ensure your sensitive financial data never falls into the wrong hands.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-12 not-prose">
        <div className="bg-[#00261C] border border-[#EDF5F2]/10 p-6 rounded-xl">
          <Shield className="w-8 h-8 text-[#B2F273] mb-4" />
          <h4 className="text-white font-bold text-lg mb-2">SOC 2 Type II</h4>
          <p className="text-[#EDF5F2]/60 text-sm">
            We undergo annual independent audits to verify our security controls, availability, and confidentiality.
          </p>
        </div>
        <div className="bg-[#00261C] border border-[#EDF5F2]/10 p-6 rounded-xl">
          <Lock className="w-8 h-8 text-[#B2F273] mb-4" />
          <h4 className="text-white font-bold text-lg mb-2">End-to-End Encryption</h4>
          <p className="text-[#EDF5F2]/60 text-sm">
            Data is encrypted in transit via TLS 1.3 and at rest using AES-256 with AWS KMS managed keys.
          </p>
        </div>
        <div className="bg-[#00261C] border border-[#EDF5F2]/10 p-6 rounded-xl">
          <Server className="w-8 h-8 text-[#B2F273] mb-4" />
          <h4 className="text-white font-bold text-lg mb-2">Data Residency</h4>
          <p className="text-[#EDF5F2]/60 text-sm">
            Enterprise customers can choose to host their data in specific regions (US, EU, SG) to meet compliance needs.
          </p>
        </div>
        <div className="bg-[#00261C] border border-[#EDF5F2]/10 p-6 rounded-xl">
          <FileCheck className="w-8 h-8 text-[#B2F273] mb-4" />
          <h4 className="text-white font-bold text-lg mb-2">Regular Pen Testing</h4>
          <p className="text-[#EDF5F2]/60 text-sm">
            We engage top-tier security firms to perform quarterly penetration tests on our infrastructure and API.
          </p>
        </div>
      </div>

      <h3>Infrastructure Security</h3>
      <p>
        Our platform runs on Amazon Web Services (AWS), utilizing their world-class data center security. We employ a zero-trust network architecture where every service-to-service call is authenticated and authorized.
      </p>

      <h3>Data Privacy</h3>
      <p>
        We strictly separate customer data. Your trade documents are stored in dedicated S3 buckets with unique encryption keys. We enforce strict role-based access control (RBAC) internally; no engineer has standing access to customer production data.
      </p>

      <h3>Vulnerability Disclosure</h3>
      <p>
        We value the contributions of the security research community. If you believe you've found a vulnerability in TRDR Hub, please report it to <a href="mailto:security@trdrhub.com">security@trdrhub.com</a>. We offer a bug bounty program for valid disclosures.
      </p>
    </LegalLayout>
  );
};

export default SecurityPage;
