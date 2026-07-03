// /tools/eudr-readiness-check — SEO landing (Phase 3, playbook §3.2).
// Keywords: "EUDR due diligence statement supplier", "EUDR compliance checklist exporter".
import ReadinessLanding from "./ReadinessLanding";

export default function EudrReadinessLanding() {
  return (
    <ReadinessLanding
      tool="eudr"
      seo={{
        title: "EUDR Readiness Check for Suppliers & Exporters — Am I in scope? | TRDR Hub",
        description:
          "Free EUDR scope check for exporters of leather, coffee, cocoa, rubber, palm oil, soy and wood products: is EU Regulation 2023/1115 about to hit your shipments? Instant answer, plus a cited readiness report covering geolocation, cutoff evidence and legality documentation.",
        path: "/tools/eudr-readiness-check",
      }}
      heroTitle="EUDR: your EU buyer needs"
      heroAccent="plot-level proof from you."
      heroSub={
        "The EU Deforestation Regulation covers cattle (including leather), cocoa, coffee, oil " +
        "palm, rubber, soya and wood — and the products made from them. EU operators must file a " +
        "due diligence statement per shipment, built on geolocation coordinates, " +
        "deforestation-free evidence and legality documents that only you, the supplier, can provide."
      }
      anchors={[
        {
          title: "Large EU operators comply from 30 December 2026",
          body: "SMEs follow 30 June 2027 (dates as postponed by Regulation (EU) 2025/2650). Buyers are collecting supplier data now.",
        },
        {
          title: "Plot-level geolocation is mandatory",
          body: "Coordinates for every plot of production land — polygons for plots over 4 hectares. No coordinates, no compliant DDS, no shipment.",
        },
        {
          title: "The cutoff date is 31 December 2020",
          body: "Products must come from land not deforested or degraded after that date — buyers cross-check coordinates against satellite data.",
        },
        {
          title: "Leather is in scope",
          body: "Cattle coverage includes hides, leather and leather goods — a major exposure for leather-exporting countries.",
        },
      ]}
      reportProductId="eudr_report"
    />
  );
}
