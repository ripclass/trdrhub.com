import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const faqs = [
  {
    question: "How accurate is the AI validation?",
    answer: "Our engine achieves 99% accuracy on discrepancy detection. We validate against 3,500+ rules from UCP600, ISBP745, and 60+ country regulations. The AI has been trained on thousands of real LC documents and bank rejection patterns.",
  },
  {
    question: "Which document types do you support?",
    answer: "We support all standard trade documents: Letters of Credit (MT700, ISO20022, PDF), Bills of Lading (paper and eBL formats including DCSA, BOLERO, essDOCS), Commercial Invoices, Packing Lists, Insurance Certificates, Certificates of Origin, and more.",
  },
  {
    question: "How long does validation take?",
    answer: "Average processing time is 45 seconds for a complete document set (6 documents). This includes OCR extraction, cross-document validation, and compliance report generation. Larger document sets scale linearly.",
  },
  {
    question: "Do you support my country's regulations?",
    answer: "Yes. We have pre-built rules for 60+ countries including Singapore, UAE, Bangladesh, India, China, US, UK, EU, and more. Our engine covers country-specific requirements like Bangladesh LCAF, India IEC, Nigeria Form M, and regional trade agreements like RCEP, CPTPP, and USMCA.",
  },
  {
    question: "What happens if the AI misses a discrepancy?",
    answer: "While rare, if our system misses a discrepancy that results in a bank rejection, we offer a discrepancy fee guarantee for Pro and Enterprise customers. We'll reimburse the bank's discrepancy fee up to $150 per incident.",
  },
  {
    question: "Can I integrate this with my existing systems?",
    answer: "Yes. We offer a REST API for programmatic access, webhook notifications for automated workflows, and direct integrations with popular ERP systems. Enterprise customers get custom integration support.",
  },
  {
    question: "Is my data secure?",
    answer: "Absolutely. All documents are encrypted in transit (TLS 1.3) and at rest (AES-256). We're SOC 2 Type II compliant and GDPR ready. Documents are automatically deleted after 30 days unless you choose to retain them longer.",
  },
  {
    question: "What's the pricing model?",
    answer: "We offer flexible pricing: Free tier for up to 5 validations/month, Pro at $49/month for unlimited validations, and Enterprise with custom pricing for high-volume users. No per-document fees on paid plans.",
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
