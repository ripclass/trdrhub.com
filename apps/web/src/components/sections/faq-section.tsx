import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

// Honest answers only (launch honesty rubric): no invented accuracy stats,
// no unverified certifications, ISBP 821 (not 745), concierge-first pricing.
const faqs = [
  {
    question: "What exactly do I get back?",
    answer:
      "A cited discrepancy report: every finding referenced to the UCP 600 article or ISBP 821 paragraph it derives from, quoting the LC clause and the evidence in your document, with a suggested fix. A trade documentation specialist reviews every report before it ships — you're never handed raw machine output. Download the sample report to see the format.",
  },
  {
    question: "How fast is the turnaround?",
    answer:
      "Standard reviews are delivered within 24 hours of submission — usually much faster. If you're up against a presentation deadline, Priority Review guarantees a 6-hour turnaround.",
  },
  {
    question: "Which document types do you support?",
    answer:
      "All standard trade documents: Letters of Credit (MT700, ISO 20022, or plain PDF), Bills of Lading, Commercial Invoices, Packing Lists, Insurance Certificates, Certificates of Origin, and more. PDF, scan, or a phone photo — if we can't read something, we ask rather than guess.",
  },
  {
    question: "What rules do you check against?",
    answer:
      "UCP 600 and ISBP 821 for documentary credits, URDG 758 and ISP98 where relevant, plus sanctions screening against OFAC, UN and UK OFSI lists. The rules engine is deterministic — rule outcomes are never left to an AI's mood — and a specialist reviews the result.",
  },
  {
    question: "Do you cover the import side too?",
    answer:
      "Yes. Exporters ask \"will my presentation comply?\"; importers ask \"is this LC safe to accept?\" — risky clauses, soft clauses, document requirements you can't actually meet. Same price, same turnaround, either side.",
  },
  {
    question: "Is my data secure and confidential?",
    answer:
      "Documents are encrypted in transit and at rest, used only to produce your report, and never shared. We'll sign an NDA before you send anything if you prefer. Ask us to delete your documents at any time.",
  },
  {
    question: "What if I'm not satisfied?",
    answer:
      "Full refund, no questions. If a report doesn't help you present cleaner documents, we don't want your money.",
  },
  {
    question: "What does it cost?",
    answer:
      "LC pack review $29 · pack review + bank-ready memo $49 · priority 6-hour review $79. CBAM or EUDR readiness reports are $149 each, or $249 for both. Prices in USD; pay in your local currency at checkout. Checking documents every week? Talk to us about a monthly arrangement.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-24 md:py-32 bg-[#00261C] relative">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

      {/* Top border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          {/* Section header */}
          <div className="text-center mb-16">
            <p className="text-[#B2F273] font-semibold mb-4 tracking-wide uppercase text-sm">FAQ</p>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6 leading-tight font-display">
              Quick answers to
              <br />
              <span className="text-[#EDF5F2]/60">questions you may have</span>
            </h2>
            <p className="text-[#EDF5F2]/60">
              Can't find what you're looking for? Contact us at{" "}
              <a href="mailto:support@trdrhub.com" className="text-[#B2F273] hover:underline">
                support@trdrhub.com
              </a>
            </p>
          </div>

          {/* FAQ Accordion */}
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div
                key={index}
                className="border border-[#EDF5F2]/10 rounded-xl overflow-hidden bg-[#00382E]/50"
              >
                <button
                  onClick={() => setOpenIndex(openIndex === index ? null : index)}
                  className="w-full flex items-center justify-between p-6 text-left hover:bg-[#00382E] transition-colors"
                >
                  <span className="font-semibold text-white pr-8 font-display">
                    {faq.question}
                  </span>
                  <ChevronDown
                    className={cn(
                      "w-5 h-5 text-[#B2F273] transition-transform shrink-0",
                      openIndex === index && "rotate-180"
                    )}
                  />
                </button>
                <div
                  className={cn(
                    "grid transition-all duration-200 ease-out",
                    openIndex === index ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                  )}
                >
                  <div className="overflow-hidden">
                    <p className="px-6 pb-6 text-[#EDF5F2]/60 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
