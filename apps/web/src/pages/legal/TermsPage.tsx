import { LegalLayout } from "./LegalLayout";

const TermsPage = () => {
  return (
    <LegalLayout title="Terms of Service" lastUpdated="January 15, 2026">
      <p>
        Please read these Terms of Service ("Terms") carefully before using the TRDR Hub platform operated by Enso Intelligence ("us", "we", or "our").
      </p>

      <h3>1. Acceptance of Terms</h3>
      <p>
        By accessing or using our Service, you agree to be bound by these Terms. If you disagree with any part of the terms, then you may not access the Service.
      </p>

      <h3>2. Description of Service</h3>
      <p>
        TRDR Hub provides AI-powered tools for trade document validation, sanctions screening, and compliance management. 
        <strong>We are a technology provider, not a bank or legal advisor.</strong> Our validation results are for informational purposes only and should not be considered as legal or financial advice.
      </p>

      <h3>3. User Accounts</h3>
      <p>
        When you create an account with us, you must provide information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account.
      </p>

      <h3>4. Intellectual Property</h3>
      <p>
        The Service and its original content (excluding Content provided by users), features, and functionality are and will remain the exclusive property of Enso Intelligence and its licensors.
      </p>

      <h3>5. Limitation of Liability</h3>
      <p>
        In no event shall Enso Intelligence, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the Service.
      </p>

      <h3>6. Discrepancy Fee Guarantee</h3>
      <p>
        For eligible Pro and Enterprise users, we offer a limited reimbursement for bank discrepancy fees incurred due to errors missed by our platform, subject to the specific terms outlined in your Service Level Agreement (SLA).
      </p>

      <h3>7. Governing Law</h3>
      <p>
        These Terms shall be governed and construed in accordance with the laws of Singapore, without regard to its conflict of law provisions.
      </p>

      <h3>8. Changes</h3>
      <p>
        We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material we will try to provide at least 30 days notice prior to any new terms taking effect.
      </p>

      <h3>9. Contact Us</h3>
      <p>
        If you have any questions about these Terms, please contact us at <a href="mailto:legal@trdrhub.com">legal@trdrhub.com</a>.
      </p>
    </LegalLayout>
  );
};

export default TermsPage;
