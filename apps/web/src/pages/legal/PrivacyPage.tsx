import { LegalLayout } from "./LegalLayout";

const PrivacyPage = () => {
  return (
    <LegalLayout title="Privacy Policy" lastUpdated="January 15, 2026">
      <p>
        At TRDR Hub ("we", "us", or "our"), we take the privacy and security of your trade data seriously. 
        This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our website and services.
      </p>

      <h3>1. Information We Collect</h3>
      <p>
        We collect information that you provide directly to us, including:
      </p>
      <ul>
        <li><strong>Account Information:</strong> Name, email address, company name, and role.</li>
        <li><strong>Trade Documents:</strong> Letters of Credit, Bills of Lading, Invoices, and other trade-related documents you upload for validation.</li>
        <li><strong>Payment Information:</strong> Billing address and payment method details (processed by our third-party payment processors).</li>
      </ul>

      <h3>2. How We Use Your Information</h3>
      <p>
        We use the information we collect to:
      </p>
      <ul>
        <li>Provide, maintain, and improve our services, including our AI validation models.</li>
        <li>Process transactions and send related information, including confirmations and invoices.</li>
        <li>Send you technical notices, updates, security alerts, and support messages.</li>
        <li>Respond to your comments, questions, and requests.</li>
      </ul>

      <h3>3. Data Sovereignty & AI Training</h3>
      <p>
        <strong>Your Data is Yours.</strong> We do not sell your trade data to third parties.
      </p>
      <p>
        We may use anonymized and aggregated data to improve our machine learning models. You can opt-out of this data usage for model training by contacting our support team or adjusting your organization settings (Enterprise plans only).
      </p>

      <h3>4. Data Security</h3>
      <p>
        We implement bank-grade security measures designed to protect your information, including:
      </p>
      <ul>
        <li>AES-256 encryption for data at rest.</li>
        <li>TLS 1.3 encryption for data in transit.</li>
        <li>Strict access controls and audit logging.</li>
      </ul>

      <h3>5. Your Rights</h3>
      <p>
        Depending on your location, you may have rights under GDPR, CCPA, or other privacy laws, including the right to access, correct, or delete your personal data.
      </p>

      <h3>6. Contact Us</h3>
      <p>
        If you have any questions about this Privacy Policy, please contact us at <a href="mailto:privacy@trdrhub.com">privacy@trdrhub.com</a>.
      </p>
    </LegalLayout>
  );
};

export default PrivacyPage;
