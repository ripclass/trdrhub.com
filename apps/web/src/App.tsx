import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom'
import LandingPage from './pages/landing/LandingPage'
import NotificationSettings from './pages/settings/NotificationSettings'
import ServicesDashboard from './pages/lcopilot/ServicesDashboard'
import EnterpriseGroupOverview from './pages/lcopilot/EnterpriseGroupOverview'
import EnterpriseAuditLog from './pages/lcopilot/EnterpriseAuditLog'
import StatusPage from './pages/StatusPage'
import Index from './pages/Index'
import TRDRHub from './pages/TRDRHub'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import ReportPage from './pages/ReportPage'
import TechnologyPage from './pages/TechnologyPage'
import ToolsPage from './pages/ToolsPage'
import ProoflineLanding from './pages/proofline/ProoflineLanding'
import ProoflineNewCase from './pages/proofline/ProoflineNewCase'
import ProoflineCases from './pages/proofline/ProoflineCases'
import ProoflineCaseDetail from './pages/proofline/ProoflineCaseDetail'
import DocsPage from './pages/resources/DocsPage'
import APIPage from './pages/resources/APIPage'
import UCP600Page from './pages/resources/UCP600Page'
import BlogPage from './pages/resources/BlogPage'
import PricingPage from './pages/PricingPage'
import CheckPage from './pages/CheckPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import PrivacyPage from './pages/legal/PrivacyPage'
import TermsPage from './pages/legal/TermsPage'
import SecurityPage from './pages/legal/SecurityPage'
// Tool landing pages — Phase 4 (2026-07 launch): only LCopilot, Sanctions,
// CBAM Check and EUDR Check are live. Every other tool routes to
// ParkedToolPage (code stays in-tree under pages/tools/; only the routes
// point at the parked page). Un-park by restoring the import + routes ONLY
// after the tool passes: works e2e with real data, zero maintenance, and
// doesn't dilute the compliance positioning.
import SanctionsScreenerLanding from './pages/tools/SanctionsScreenerLanding'
import ParkedToolPage from './pages/ParkedToolPage'
import {
  SanctionsLayout,
  SanctionsOverview,
  SanctionsScreenParty,
  SanctionsScreenVessel,
  SanctionsScreenGoods,
  SanctionsHistory as SanctionsHistoryPage,
  SanctionsCertificates,
  SanctionsWatchlist,
  SanctionsSettings as SanctionsSettingsPage,
  SanctionsHelp as SanctionsHelpPage,
  SanctionsBatchUpload,
  SanctionsAPIAccess,
} from './pages/tools/sanctions'
import CareersPage from './pages/CareersPage'
import Login from './pages/Login'
import Register from './pages/Register'
import Onboarding from './pages/Onboarding'
import LcopilotRouter from './pages/LcopilotRouter'
// Legacy Dashboard.tsx (mock-data, "Dhaka Exports Ltd" hardcodes) deleted
// 2026-05-10. /dashboard now redirects to /lcopilot/dashboard.
import UploadLC from './pages/UploadLC'
import DraftLCCorrections from './pages/DraftLCCorrections'
import DraftLCRiskResults from './pages/DraftLCRiskResults'
import ExportLCUpload from './pages/ExportLCUpload'
import ImportLCUpload from './pages/ImportLCUpload'
import ImportResults from './pages/ImportResults'
import ImportResultsSimple from './pages/ImportResultsSimple'
import ExporterDashboard from './pages/ExporterDashboard'
import ExporterResults from './pages/ExporterResults'
import ExporterResultsV2 from './pages/ExporterResultsV2'
import ExporterAnalytics from './pages/ExporterAnalytics'
import AnalyticsPage from './pages/dashboard/analytics/index'
import ExporterAnalyticsPage from './pages/dashboard/analytics/exporter'
import BankAnalyticsPage from './pages/dashboard/analytics/bank'
import BankDashboard from './pages/BankDashboard'
import BankDashboardV2 from './pages/BankDashboardV2'
import BankLogin from './pages/bank/BankLogin'
import ImporterDashboardV2 from './pages/ImporterDashboardV2'
import ClientDashboard from './pages/ClientDashboard'
import ComponentGallery from './pages/ComponentGallery'
import ExporterDocumentCorrections from './pages/ExporterDocumentCorrections'
import SupplierDocumentCorrections from './pages/SupplierDocumentCorrections'
import SupplierDocumentResults from './pages/SupplierDocumentResults'
import Support from './pages/Support'
import NotFound from './pages/NotFound'
import StubModeIndicator from './components/StubModeIndicator'
import DiscrepancyListDemo from './components/DiscrepancyListDemo'
import AdminLogin from './pages/admin/AdminLogin'
import AdminShell from './pages/admin/AdminShell'
import AuthCallback from './pages/auth/Callback'
import { BankAuthProvider } from './lib/bank/auth'
import { LcopilotBetaRoute } from './components/lcopilot/LcopilotBetaRoute'
import AgencyDashboard from './pages/lcopilot/AgencyDashboard'
import StartReview from './pages/lcopilot/StartReview'
import CbamReadinessLanding from './pages/tools/readiness/CbamReadinessLanding'
import EudrReadinessLanding from './pages/tools/readiness/EudrReadinessLanding'
import ReadinessApply from './pages/tools/readiness/ReadinessApply'
import GroupOverview from './pages/lcopilot/GroupOverview'
import { ImporterValidationPage } from './pages/importer/ImporterValidationPage'
import { isBulkValidationEnabled, isImporterV2Enabled } from './lib/lcopilot/featureFlags'
import BulkValidateTest from './pages/lcopilot/BulkValidateTest'
import RepaperRecipient from './pages/lcopilot/RepaperRecipient'
import { RequireAuth } from './components/lcopilot/RequireAuth'
// /hub retired 2026-05-10 — single-product framing means LCopilot is the home.
// The route below redirects /hub and all subroutes to /lcopilot/dashboard.
// The src/pages/hub/ page files were deleted in 607a1705.
function LegacyExporterResultsRedirect() {
  const location = useLocation()
  const { jobId } = useParams()
  const params = new URLSearchParams(location.search)

  if (jobId && !params.has('jobId')) {
    params.set('jobId', jobId)
  }
  if (!params.has('section')) {
    params.set('section', 'reviews')
  }

  return <Navigate to={`/lcopilot/exporter-dashboard?${params.toString()}`} replace />
}

// Concierge status tracker lives inside the dashboard shell (section=status).
// This keeps every /lcopilot/status/{jobId} link — backend responses,
// notifications, delivery emails — working while landing users in the app
// chrome instead of a bare standalone page.
function StatusToDashboardRedirect() {
  const location = useLocation()
  const { jobId } = useParams()
  const params = new URLSearchParams(location.search)

  if (jobId && !params.has('jobId')) {
    params.set('jobId', jobId)
  }
  params.set('section', 'status')

  return <Navigate to={`/lcopilot/exporter-dashboard?${params.toString()}`} replace />
}

// Main App Component
function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/debug" element={<div style={{padding: '20px', fontSize: '24px'}}>🎉 Debug Route Works! The server and routing are functioning correctly.</div>} />
        <Route path="/lc-demo" element={<Index />} />
        <Route path="/trdr" element={<TRDRHub />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/proofline" element={<ProoflineLanding />} />
        <Route path="/proofline/new" element={<RequireAuth><ProoflineNewCase /></RequireAuth>} />
        <Route path="/proofline/cases" element={<RequireAuth><ProoflineCases /></RequireAuth>} />
        <Route path="/proofline/cases/:caseId" element={<RequireAuth><ProoflineCaseDetail /></RequireAuth>} />
        <Route path="/technology" element={<TechnologyPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/api" element={<APIPage />} />
        <Route path="/guides/ucp600" element={<UCP600Page />} />
        <Route path="/blog" element={<BlogPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/check" element={<CheckPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/careers" element={<CareersPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/security" element={<SecurityPage />} />
        
        {/* Tool Landing Pages - Live */}
        <Route path="/sanctions" element={<SanctionsScreenerLanding />} />
        {/* Sanctions Screener Dashboard with Sidebar */}
        <Route path="/sanctions/dashboard" element={<SanctionsLayout />}>
          <Route index element={<SanctionsOverview />} />
          <Route path="screen/party" element={<SanctionsScreenParty />} />
          <Route path="screen/vessel" element={<SanctionsScreenVessel />} />
          <Route path="screen/goods" element={<SanctionsScreenGoods />} />
          <Route path="batch" element={<SanctionsBatchUpload />} />
          <Route path="history" element={<SanctionsHistoryPage />} />
          <Route path="certificates" element={<SanctionsCertificates />} />
          <Route path="watchlist" element={<SanctionsWatchlist />} />
          <Route path="api" element={<SanctionsAPIAccess />} />
          <Route path="settings" element={<SanctionsSettingsPage />} />
          <Route path="help" element={<SanctionsHelpPage />} />
        </Route>
        {/* Parked tools — Phase 4 (2026-07 launch). Wildcards cover the old
            dashboard subroutes so deep links land on the parked page too. */}
        <Route path="/hs-code/*" element={<ParkedToolPage />} />
        <Route path="/doc-generator/*" element={<ParkedToolPage />} />
        <Route path="/lc-builder/*" element={<ParkedToolPage />} />
        <Route path="/tracking/*" element={<ParkedToolPage />} />
        <Route path="/analytics" element={<ParkedToolPage />} />
        <Route path="/price-verify/*" element={<ParkedToolPage />} />
        <Route path="/risk" element={<ParkedToolPage />} />
        <Route path="/dual-use" element={<ParkedToolPage />} />
        <Route path="/customs" element={<ParkedToolPage />} />
        <Route path="/duty-calc" element={<ParkedToolPage />} />
        <Route path="/routes" element={<ParkedToolPage />} />
        <Route path="/bank-fees" element={<ParkedToolPage />} />
        <Route path="/finance" element={<ParkedToolPage />} />
        <Route path="/insurance" element={<ParkedToolPage />} />
        <Route path="/lcopilot" element={<Index />} />
        {/* Phase 3 — CBAM/EUDR readiness tools (SEO landings + paid intake) */}
        <Route path="/tools/cbam-readiness-check" element={<CbamReadinessLanding />} />
        <Route path="/tools/eudr-readiness-check" element={<EudrReadinessLanding />} />
        <Route path="/tools/readiness/apply" element={<RequireAuth><ReadinessApply /></RequireAuth>} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/onboarding" element={
          <LcopilotBetaRoute scope="onboarding">
            <Onboarding />
          </LcopilotBetaRoute>
        } />
        
        {/* Hub retired 2026-05-10 — LCopilot is the single shipped product
            for launch. /hub and all subroutes redirect to /lcopilot/dashboard,
            which activity-resolves to the user's exporter/importer/agency
            dashboard. Redirect retained ≥90 days so old links + bookmarks +
            in-app "Back to Hub" sidebar links keep working until the next
            housekeeping pass strips them. */}
        <Route path="/hub" element={<Navigate to="/lcopilot/dashboard" replace />} />
        <Route path="/hub/*" element={<Navigate to="/lcopilot/dashboard" replace />} />
        <Route path="/dashboard" element={<Navigate to="/lcopilot/dashboard" replace />} />
        <Route path="/settings/notifications" element={<RequireAuth><NotificationSettings /></RequireAuth>} />
        {/* Phase 1 concierge — customer-facing review status tracker. */}
        <Route path="/lcopilot/status/:jobId" element={<RequireAuth><StatusToDashboardRedirect /></RequireAuth>} />
        {/* Concierge entry point — authed → upload; anonymous → fast-path signup. */}
        <Route path="/lcopilot/start-review" element={<StartReview />} />
        <Route path="/lcopilot/services-dashboard" element={<RequireAuth><ServicesDashboard /></RequireAuth>} />
        <Route path="/lcopilot/group-overview" element={<RequireAuth><EnterpriseGroupOverview /></RequireAuth>} />
        <Route path="/lcopilot/audit-log" element={<RequireAuth><EnterpriseAuditLog /></RequireAuth>} />
        <Route path="/lcopilot/upload" element={<RequireAuth><UploadPage /></RequireAuth>} />
        <Route path="/lcopilot/review/:sessionId" element={<RequireAuth><ReviewPage /></RequireAuth>} />
        <Route path="/lcopilot/report/:sessionId" element={<RequireAuth><ReportPage /></RequireAuth>} />
        <Route path="/lcopilot/demo" element={<DiscrepancyListDemo />} />
        <Route path="/lcopilot/dashboard" element={
          <LcopilotBetaRoute scope="router">
            <LcopilotRouter />
          </LcopilotBetaRoute>
        } />
        <Route path="/lcopilot/upload-lc" element={<RequireAuth><UploadLC /></RequireAuth>} />
        <Route path="/lcopilot/results" element={<LegacyExporterResultsRedirect />} />
        <Route path="/lcopilot/results/:jobId" element={<LegacyExporterResultsRedirect />} />
        {/* V2 Results - Output-First SME-focused design */}
        <Route path="/lcopilot/results-v2/:sessionId" element={<RequireAuth><ExporterResultsV2 /></RequireAuth>} />
        <Route path="/lcopilot/draft-corrections" element={<RequireAuth><DraftLCCorrections /></RequireAuth>} />
        <Route path="/lcopilot/draft-risk-results" element={<RequireAuth><DraftLCRiskResults /></RequireAuth>} />
        <Route path="/export-lc-upload" element={<RequireAuth><ExportLCUpload /></RequireAuth>} />
        <Route path="/lcopilot/import-upload" element={<RequireAuth><ImportLCUpload /></RequireAuth>} />
        <Route path="/import/results/:jobId" element={<RequireAuth><ImportResults /></RequireAuth>} />
        <Route path="/lcopilot/import-results/:jobId" element={<RequireAuth><ImportResults /></RequireAuth>} />
        {/* Redirect old exporter login URL to main login */}
        <Route path="/lcopilot/exporter-dashboard/login" element={
          <Navigate to="/login?returnUrl=/lcopilot/exporter-dashboard" replace />
        } />
        <Route path="/lcopilot/exporter-dashboard" element={
          <LcopilotBetaRoute scope="exporter">
            <ExporterDashboard />
          </LcopilotBetaRoute>
        } />
        {/* Combined/Enterprise dashboards retired 2026-04-23 — multi-activity users
            now land on their first activity's dashboard with the WorkspaceSwitcher
            in the header (see memory/project_lcopilot_onboarding_redesign.md).
            Redirect retained for ≥90 days so old links and bookmarks don't 404. */}
        <Route path="/lcopilot/combined-dashboard" element={
          <Navigate to="/lcopilot/exporter-dashboard" replace />
        } />
        <Route path="/lcopilot/exporter-dashboard/legacy" element={<Navigate to="/lcopilot/exporter-dashboard" replace />} />
        <Route path="/lcopilot/exporter-dashboard/v2" element={<Navigate to="/lcopilot/exporter-dashboard" replace />} />
        <Route path="/lcopilot/importer-dashboard/login" element={
          <Navigate to="/login?returnUrl=/lcopilot/importer-dashboard" replace />
        } />
        <Route path="/lcopilot/importer-dashboard" element={
          <LcopilotBetaRoute scope="importer">
            <ImporterDashboardV2 />
          </LcopilotBetaRoute>
        } />
        {isImporterV2Enabled() && (
          <>
            <Route path="/lcopilot/importer-dashboard/draft-lc" element={
              <LcopilotBetaRoute scope="importer">
                <ImporterValidationPage moment="draft_lc" />
              </LcopilotBetaRoute>
            } />
            <Route path="/lcopilot/importer-dashboard/supplier-docs" element={
              <LcopilotBetaRoute scope="importer">
                <ImporterValidationPage moment="supplier_docs" />
              </LcopilotBetaRoute>
            } />
          </>
        )}
        {/* Phase A1 part 2 — bulk validation QA tester (hidden, no nav link). */}
        {isBulkValidationEnabled() && (
          <Route path="/lcopilot/_bulk-test" element={
            <RequireAuth>
              <BulkValidateTest />
            </RequireAuth>
          } />
        )}
        {/* Phase A2 — re-papering recipient page. Public-by-token, NOT auth-gated. */}
        <Route path="/repaper/:token" element={<RepaperRecipient />} />
        <Route path="/lcopilot/enterprise-dashboard" element={
          <Navigate to="/lcopilot/exporter-dashboard" replace />
        } />
        {/* Day 4: agency dashboard placeholder for sourcing/buying-agent users. */}
        <Route path="/lcopilot/agency-dashboard" element={
          <LcopilotBetaRoute scope="agency">
            <AgencyDashboard />
          </LcopilotBetaRoute>
        } />
        {/* Day 4: enterprise-tier cross-SBU rollup placeholder. */}
        <Route path="/lcopilot/group-overview" element={
          <RequireAuth>
            <GroupOverview />
          </RequireAuth>
        } />
        <Route path="/lcopilot/exporter-results" element={<LegacyExporterResultsRedirect />} />
        <Route path="/lcopilot/exporter-analytics" element={<RequireAuth><ExporterAnalytics /></RequireAuth>} />
        {/* Phase 4/6: /importer-analytics folded into the dashboard stats strip */}
        <Route path="/lcopilot/importer-analytics" element={<Navigate to="/lcopilot/importer-dashboard" replace />} />
        <Route path="/lcopilot/analytics" element={<RequireAuth><AnalyticsPage /></RequireAuth>} />
        <Route path="/lcopilot/analytics/exporter" element={<RequireAuth><ExporterAnalyticsPage /></RequireAuth>} />
        <Route path="/lcopilot/analytics/bank" element={<RequireAuth><BankAnalyticsPage /></RequireAuth>} />
        <Route path="/lcopilot/bank-dashboard/login" element={
          <BankAuthProvider>
            <BankLogin />
          </BankAuthProvider>
        } />
        <Route path="/lcopilot/bank-dashboard" element={
          <BankAuthProvider>
            <BankDashboardV2 />
          </BankAuthProvider>
        } />
        <Route path="/lcopilot/bank-dashboard/legacy" element={<BankDashboard />} />
        <Route path="/lcopilot/bank-dashboard/client/:clientName" element={
          <BankAuthProvider>
            <ClientDashboard />
          </BankAuthProvider>
        } />
        <Route path="/lcopilot/component-gallery" element={<ComponentGallery />} />
        <Route path="/lcopilot/exporter-corrections" element={<RequireAuth><ExporterDocumentCorrections /></RequireAuth>} />
        <Route path="/lcopilot/supplier-corrections" element={<RequireAuth><SupplierDocumentCorrections /></RequireAuth>} />
        <Route path="/lcopilot/supplier-results" element={<RequireAuth><SupplierDocumentResults /></RequireAuth>} />
        <Route path="/test-import" element={<ImportResultsSimple />} />
        <Route path="/lcopilot/support" element={<Support />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminShell />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <StubModeIndicator />

    </>
  )
}

export default App
