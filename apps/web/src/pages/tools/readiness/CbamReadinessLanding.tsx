// /tools/cbam-readiness-check — SEO landing (Phase 3, playbook §3.2).
// Keywords: "CBAM supplier requirements", "CBAM readiness check".
import ReadinessLanding from "./ReadinessLanding";

export default function CbamReadinessLanding() {
  return (
    <ReadinessLanding
      tool="cbam"
      seo={{
        title: "CBAM Readiness Check for Suppliers — Am I in scope? | TRDR Hub",
        description:
          "Free CBAM scope check for non-EU manufacturers and exporters: is your steel, aluminium, cement, fertiliser or hydrogen in scope of EU Regulation 2023/956? Instant answer, plus a cited supplier-readiness report your EU buyer can use.",
        path: "/tools/cbam-readiness-check",
      }}
      heroTitle="CBAM is live. Your EU buyers"
      heroAccent="need your emissions data."
      heroSub={
        "The EU's Carbon Border Adjustment Mechanism prices the carbon embedded in iron & steel, " +
        "aluminium, cement, fertilisers, hydrogen and electricity imported into the EU. Your " +
        "importers file the declarations — but the data they file comes from you. Suppliers who " +
        "can hand over verified emissions data keep the business."
      }
      anchors={[
        {
          title: "The definitive regime has applied since 1 January 2026",
          body: "Reporting is no longer a trial run — 2026 imports carry real certificate costs.",
        },
        {
          title: "Certificates go on sale February 2027 — retroactive to 2026",
          body: "Your importers' first annual declaration (due 30 September 2027) covers this year's shipments.",
        },
        {
          title: "The 50-tonne de minimis exempts ~90% of importers",
          body: "But the importers still in scope carry ~99% of embedded emissions — if your buyer imports serious volume, they're in.",
        },
        {
          title: "No data from you = punitive default values for them",
          body: "Importers without actual supplier emissions data must use default values that usually cost more — and they know it.",
        },
      ]}
      reportProductId="cbam_report"
    />
  );
}
