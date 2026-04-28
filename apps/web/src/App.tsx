import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom'
import LandingPage from './pages/landing/LandingPage'
import NotificationSettings from './pages/settings/NotificationSettings'
import ServicesDashboard from './pages/lcopilot/ServicesDashboard'
import EnterpriseGroupOverview from './pages/lcopilot/EnterpriseGroupOverview'
import EnterpriseAuditLog from './pages/lcopilot/EnterpriseAuditLog'
import Index from './pages/Index'
import TRDRHub from './pages/TRDRHub'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import ReportPage from './pages/ReportPage'
import TechnologyPage from './pages/TechnologyPage'
import ToolsPage from './pages/ToolsPage'
import DocsPage from './pages/resources/DocsPage'
import APIPage from './pages/resources/APIPage'
import UCP600Page from './pages/resources/UCP600Page'
import BlogPage from './pages/resources/BlogPage'
import PricingPage from './pages/PricingPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import PrivacyPage from './pages/legal/PrivacyPage'
import TermsPage from './pages/legal/TermsPage'
import SecurityPage from './pages/legal/SecurityPage'
// Tool landing pages
import SanctionsScreenerLanding from './pages/tools/SanctionsScreenerLanding'
import HSCodeFinderLanding from './pages/tools/HSCodeFinderLanding'
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
import {
  HSCodeLayout,
  HSCodeOverview,
  HSCodeClassify,
  HSCodeSearch,
  HSCodeDuty,
  HSCodeFTA,
  HSCodeROO,
  HSCodeCompliance,
  HSCodeHistory as HSCodeHistoryPage,
  HSCodeFavorites,
  HSCodeBulk,
  HSCodeSettings,
  HSCodeHelp,
  HSCodeCompare,
  HSCodeRulings,
  HSCodeAlerts,
  HSCodeUSMCA,
  HSCodeTeams,
  HSCodeComplianceDashboard,
  HSCodeExportControls,
  HSCodeSection301,
  HSCodeADCVD,
  HSCodeQuotas,
} from './pages/tools/hs-code'
import DocGeneratorLanding from './pages/tools/DocGeneratorLanding'
import LCBuilderLanding from './pages/tools/LCBuilderLanding'
import LCBuilderDashboard from './pages/tools/lc-builder/LCBuilderDashboard'
import LCBuilderWizard from './pages/tools/lc-builder/LCBuilderWizard'
import LCBuilderLayout from './pages/tools/lc-builder/LCBuilderLayout'
import ClauseLibraryPage from './pages/tools/lc-builder/ClauseLibraryPage'
import LCTemplatesPage from './pages/tools/lc-builder/LCTemplatesPage'
import ApplicantProfilesPage from './pages/tools/lc-builder/ApplicantProfilesPage'
import BeneficiaryDirectoryPage from './pages/tools/lc-builder/BeneficiaryDirectoryPage'
import MT700ReferencePage from './pages/tools/lc-builder/MT700ReferencePage'
import RiskCalculatorPage from './pages/tools/lc-builder/RiskCalculatorPage'
import LCBuilderSettingsPage from './pages/tools/lc-builder/LCBuilderSettingsPage'
import LCBuilderHelpPage from './pages/tools/lc-builder/LCBuilderHelpPage'
import VersionHistoryPage from './pages/tools/lc-builder/VersionHistoryPage'
import LCWorkflowPage from './pages/tools/lc-builder/LCWorkflowPage'
import SharedWithMePage from './pages/tools/lc-builder/SharedWithMePage'
import ContainerTrackerLanding from './pages/tools/ContainerTrackerLanding'
import TradeAnalyticsLanding from './pages/tools/TradeAnalyticsLanding'
import PriceVerifyLanding from './pages/tools/PriceVerifyLanding'
import PriceVerify from './pages/tools/PriceVerify'
import { 
  PriceVerifyDashboard, 
  DashboardOverview, 
  VerifyPage,
  BatchVerifyPage,
  CommoditiesPage,
  MarketPricesPage,
  HistoryPage,
  AnalyticsPage as PVAnalyticsPage,
  ReportsPage,
  SettingsPage as PVSettingsPage,
  HelpPage,
  AdminPage as PVAdminPage,
} from './pages/tools/price-verify'
import CounterpartyRiskLanding from './pages/tools/CounterpartyRiskLanding'
import DualUseCheckerLanding from './pages/tools/DualUseCheckerLanding'
import CustomsMateLanding from './pages/tools/CustomsMateLanding'
import DutyCalculatorLanding from './pages/tools/DutyCalculatorLanding'
import RouteOptimizerLanding from './pages/tools/RouteOptimizerLanding'
import BankFeeComparatorLanding from './pages/tools/BankFeeComparatorLanding'
import TradeFinanceLanding from './pages/tools/TradeFinanceLanding'
import InsuranceQuoteLanding from './pages/tools/InsuranceQuoteLanding'
import CareersPage from './pages/CareersPage'
import Login from './pages/Login'
import Register from './pages/Register'
import Onboarding from './pages/Onboarding'
import LcopilotLanding from './pages/LcopilotLanding'
import LcopilotRouter from './pages/LcopilotRouter'
import Dashboard from './pages/Dashboard'
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
import GroupOverview from './pages/lcopilot/GroupOverview'
import { ImporterValidationPage } from './pages/importer/ImporterValidationPage'
import { isBulkValidationEnabled, isImporterV2Enabled } from './lib/lcopilot/featureFlags'
import BulkValidateTest from './pages/lcopilot/BulkValidateTest'
import RepaperRecipient from './pages/lcopilot/RepaperRecipient'
import { RequireAuth } from './components/lcopilot/RequireAuth'
import { HubLayout, HubHome, HubBilling, HubTeam, HubSettings, HubUsage } from './pages/hub'
import { 
  TrackingLayout, 
  TrackingOverview, 
  TrackingPlaceholder, 
  ContainerTrackPage, 
  VesselTrackPage,
  ContainerSearchPage,
  VesselSearchPage,
  ActiveShipmentsPage,
  AlertsPage,
  HistoryPage as TrackingHistoryPage,
  AnalyticsPage as TrackingAnalyticsPage,
  SettingsPage as TrackingSettingsPage,
  HelpPage as TrackingHelpPage,
  RouteMapPage,
  PortSchedulePage,
  ExceptionsPage,
  PerformancePage,
} from './pages/tools/tracking'
import {
  DocGeneratorLayout,
  DocGeneratorDashboard,
  CreateDocumentWizard,
  BrandingSettings,
  TemplatesPage,
  ProductCatalogPage,
  BuyerDirectoryPage,
  SignaturesPage,
  BankFormatsPage,
  CertificatesPage,
} from './pages/tools/doc-generator'

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

// Main App Component
function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/debug" element={<div style={{padding: '20px', fontSize: '24px'}}>🎉 Debug Route Works! The server and routing are functioning correctly.</div>} />
        <Route path="/lc-demo" element={<Index />} />
        <Route path="/trdr" element={<TRDRHub />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/technology" element={<TechnologyPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/api" element={<APIPage />} />
        <Route path="/guides/ucp600" element={<UCP600Page />} />
        <Route path="/blog" element={<BlogPage />} />
        <Route path="/pricing" element={<PricingPage />} />
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
        <Route path="/hs-code" element={<HSCodeFinderLanding />} />
        {/* HS Code Finder Dashboard with Sidebar */}
        <Route path="/hs-code/dashboard" element={<HSCodeLayout />}>
          <Route index element={<HSCodeOverview />} />
          <Route path="classify" element={<HSCodeClassify />} />
          <Route path="search" element={<HSCodeSearch />} />
          <Route path="duty" element={<HSCodeDuty />} />
          <Route path="fta" element={<HSCodeFTA />} />
          <Route path="roo" element={<HSCodeROO />} />
          <Route path="compliance" element={<HSCodeCompliance />} />
          <Route path="history" element={<HSCodeHistoryPage />} />
          <Route path="favorites" element={<HSCodeFavorites />} />
          <Route path="bulk" element={<HSCodeBulk />} />
          <Route path="settings" element={<HSCodeSettings />} />
          <Route path="help" element={<HSCodeHelp />} />
          {/* Phase 2 Features */}
          <Route path="compare" element={<HSCodeCompare />} />
          <Route path="rulings" element={<HSCodeRulings />} />
          <Route path="alerts" element={<HSCodeAlerts />} />
          {/* Phase 3 Features */}
          <Route path="usmca" element={<HSCodeUSMCA />} />
          <Route path="teams" element={<HSCodeTeams />} />
          {/* Phase 4 Features - Compliance Suite */}
          <Route path="compliance-suite" element={<HSCodeComplianceDashboard />} />
          <Route path="export-controls" element={<HSCodeExportControls />} />
          <Route path="section-301" element={<HSCodeSection301 />} />
          <Route path="ad-cvd" element={<HSCodeADCVD />} />
          <Route path="quotas" element={<HSCodeQuotas />} />
        </Route>
        
        {/* Tool Landing Pages */}
        <Route path="/doc-generator" element={<DocGeneratorLanding />} />
        {/* Doc Generator Dashboard with Sidebar */}
        <Route path="/doc-generator/dashboard" element={<DocGeneratorLayout />}>
          <Route index element={<DocGeneratorDashboard />} />
          <Route path="new" element={<CreateDocumentWizard />} />
          <Route path="edit/:id" element={<CreateDocumentWizard />} />
          <Route path="branding" element={<BrandingSettings />} />
          <Route path="templates" element={<TemplatesPage />} />
          <Route path="products" element={<ProductCatalogPage />} />
          <Route path="buyers" element={<BuyerDirectoryPage />} />
          <Route path="signatures" element={<SignaturesPage />} />
          <Route path="bank-formats" element={<BankFormatsPage />} />
          <Route path="certificates" element={<CertificatesPage />} />
        </Route>
        <Route path="/lc-builder" element={<LCBuilderLanding />} />
        {/* LC Builder Dashboard with Sidebar */}
        <Route path="/lc-builder/dashboard" element={<LCBuilderLayout />}>
          <Route index element={<LCBuilderDashboard />} />
          <Route path="new" element={<LCBuilderWizard />} />
          <Route path="edit/:id" element={<LCBuilderWizard />} />
          <Route path="clauses" element={<ClauseLibraryPage />} />
          <Route path="templates" element={<LCTemplatesPage />} />
          <Route path="applicants" element={<ApplicantProfilesPage />} />
          <Route path="beneficiaries" element={<BeneficiaryDirectoryPage />} />
          <Route path="mt700-reference" element={<MT700ReferencePage />} />
          <Route path="risk" element={<RiskCalculatorPage />} />
          <Route path="settings" element={<LCBuilderSettingsPage />} />
          <Route path="help" element={<LCBuilderHelpPage />} />
          <Route path="history" element={<VersionHistoryPage />} />
          <Route path="history/:applicationId" element={<VersionHistoryPage />} />
          <Route path="workflow/:id" element={<LCWorkflowPage />} />
          <Route path="approvals" element={<LCWorkflowPage />} />
          <Route path="shared" element={<SharedWithMePage />} />
        </Route>
        <Route path="/lc-builder/wizard" element={<LCBuilderWizard />} />
        <Route path="/lc-builder/wizard/:id" element={<LCBuilderWizard />} />
        <Route path="/tracking" element={<ContainerTrackerLanding />} />
        {/* Tracking Dashboard with Sidebar */}
        <Route path="/tracking/dashboard" element={<TrackingLayout />}>
          <Route index element={<TrackingOverview />} />
          <Route path="search" element={<ContainerSearchPage />} />
          <Route path="vessel-search" element={<VesselSearchPage />} />
          <Route path="container/:containerId" element={<ContainerTrackPage />} />
          <Route path="vessel/:vesselId" element={<VesselTrackPage />} />
          {/* Full Feature Pages */}
          <Route path="active" element={<ActiveShipmentsPage />} />
          <Route path="map" element={<RouteMapPage />} />
          <Route path="ports" element={<PortSchedulePage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="exceptions" element={<ExceptionsPage />} />
          <Route path="history" element={<TrackingHistoryPage />} />
          <Route path="analytics" element={<TrackingAnalyticsPage />} />
          <Route path="performance" element={<PerformancePage />} />
          <Route path="settings" element={<TrackingSettingsPage />} />
          <Route path="help" element={<TrackingHelpPage />} />
        </Route>
        <Route path="/analytics" element={<TradeAnalyticsLanding />} />
        <Route path="/price-verify" element={<PriceVerifyLanding />} />
        <Route path="/price-verify/tool" element={<PriceVerify />} />
        {/* Price Verify Dashboard */}
        <Route path="/price-verify/dashboard" element={<PriceVerifyDashboard />}>
          <Route index element={<DashboardOverview />} />
          <Route path="verify" element={<VerifyPage />} />
          <Route path="batch" element={<BatchVerifyPage />} />
          <Route path="commodities" element={<CommoditiesPage />} />
          <Route path="prices" element={<MarketPricesPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="analytics" element={<PVAnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<PVSettingsPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="admin" element={<PVAdminPage />} />
        </Route>
        <Route path="/risk" element={<CounterpartyRiskLanding />} />
        <Route path="/dual-use" element={<DualUseCheckerLanding />} />
        <Route path="/customs" element={<CustomsMateLanding />} />
        <Route path="/duty-calc" element={<DutyCalculatorLanding />} />
        <Route path="/routes" element={<RouteOptimizerLanding />} />
        <Route path="/bank-fees" element={<BankFeeComparatorLanding />} />
        <Route path="/finance" element={<TradeFinanceLanding />} />
        <Route path="/insurance" element={<InsuranceQuoteLanding />} />
        <Route path="/lcopilot" element={<Index />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/onboarding" element={
          <LcopilotBetaRoute scope="onboarding">
            <Onboarding />
          </LcopilotBetaRoute>
        } />
        
        {/* Hub - Unified Dashboard with Sidebar */}
        <Route path="/hub" element={<RequireAuth><HubLayout /></RequireAuth>}>
          <Route index element={<HubHome />} />
          <Route path="home" element={<HubHome />} />
          <Route path="usage" element={<HubUsage />} />
          <Route path="billing" element={<HubBilling />} />
          <Route path="team" element={<HubTeam />} />
          <Route path="settings" element={<HubSettings />} />
        </Route>
        <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/settings/notifications" element={<RequireAuth><NotificationSettings /></RequireAuth>} />
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
