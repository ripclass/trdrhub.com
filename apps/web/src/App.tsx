import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/landing/LandingPage'
import Index from './pages/Index'
import TRDRHub from './pages/TRDRHub'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import ReportPage from './pages/ReportPage'
import ToolsPage from './pages/ToolsPage'
import PricingPage from './pages/PricingPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
// Tool landing pages
import SanctionsScreenerLanding from './pages/tools/SanctionsScreenerLanding'
import HSCodeFinderLanding from './pages/tools/HSCodeFinderLanding'
import DocGeneratorLanding from './pages/tools/DocGeneratorLanding'
import LCBuilderLanding from './pages/tools/LCBuilderLanding'
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
import Login from './pages/Login'
import Register from './pages/Register'
import Onboarding from './pages/Onboarding'
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
import ImporterDashboard from './pages/ImporterDashboard'
import ExporterResults from './pages/ExporterResults'
import ExporterAnalytics from './pages/ExporterAnalytics'
import ImporterAnalytics from './pages/ImporterAnalytics'
import AnalyticsPage from './pages/dashboard/analytics/index'
import ExporterAnalyticsPage from './pages/dashboard/analytics/exporter'
import BankAnalyticsPage from './pages/dashboard/analytics/bank'
import BankDashboard from './pages/BankDashboard'
import BankDashboardV2 from './pages/BankDashboardV2'
import BankLogin from './pages/bank/BankLogin'
import ImporterDashboardV2 from './pages/ImporterDashboardV2'
import ExporterLogin from './pages/exporter/ExporterLogin'
import ImporterLogin from './pages/importer/ImporterLogin'
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
import CombinedDashboard from './pages/CombinedDashboard'
import EnterpriseDashboard from './pages/EnterpriseDashboard'
import { BankAuthProvider } from './lib/bank/auth'
import { ExporterAuthProvider } from './lib/exporter/auth'
import { ImporterAuthProvider } from './lib/importer/auth'
import { Toaster } from './components/ui/toaster'
import { HubLayout, HubHome, HubBilling, HubTeam, HubSettings, HubUsage } from './pages/hub'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/debug" element={<div style={{padding: '20px', fontSize: '24px'}}>🎉 Debug Route Works! The server and routing are functioning correctly.</div>} />
        <Route path="/lc-demo" element={<Index />} />
        <Route path="/trdr" element={<TRDRHub />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        
        {/* Tool Landing Pages - Live */}
        <Route path="/sanctions" element={<SanctionsScreenerLanding />} />
        <Route path="/hs-code" element={<HSCodeFinderLanding />} />
        
        {/* Tool Landing Pages - Coming Soon (Full Pages) */}
        <Route path="/doc-generator" element={<DocGeneratorLanding />} />
        <Route path="/lc-builder" element={<LCBuilderLanding />} />
        <Route path="/tracking" element={<ContainerTrackerLanding />} />
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
        <Route path="/onboarding" element={<Onboarding />} />
        
        {/* Hub - Unified Dashboard with Sidebar */}
        <Route path="/hub" element={<HubLayout />}>
          <Route index element={<HubHome />} />
          <Route path="home" element={<HubHome />} />
          <Route path="usage" element={<HubUsage />} />
          <Route path="billing" element={<HubBilling />} />
          <Route path="team" element={<HubTeam />} />
          <Route path="settings" element={<HubSettings />} />
        </Route>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/lcopilot/upload" element={<UploadPage />} />
        <Route path="/lcopilot/review/:sessionId" element={<ReviewPage />} />
        <Route path="/lcopilot/report/:sessionId" element={<ReportPage />} />
        <Route path="/lcopilot/demo" element={<DiscrepancyListDemo />} />
        <Route path="/lcopilot/dashboard" element={<LcopilotRouter />} />
        <Route path="/lcopilot/upload-lc" element={<UploadLC />} />
        <Route path="/lcopilot/results" element={<ExporterResults />} />
        <Route path="/lcopilot/results/:jobId" element={<ExporterResults />} />
        <Route path="/lcopilot/draft-corrections" element={<DraftLCCorrections />} />
        <Route path="/lcopilot/draft-risk-results" element={<DraftLCRiskResults />} />
        <Route path="/export-lc-upload" element={<ExportLCUpload />} />
        <Route path="/lcopilot/import-upload" element={<ImportLCUpload />} />
        <Route path="/import/results/:jobId" element={<ImportResults />} />
        <Route path="/lcopilot/import-results/:jobId" element={<ImportResults />} />
        {/* Redirect old exporter login URL to main login */}
        <Route path="/lcopilot/exporter-dashboard/login" element={
          <Navigate to="/login?returnUrl=/lcopilot/exporter-dashboard" replace />
        } />
        <Route path="/lcopilot/exporter-dashboard" element={
          <ExporterAuthProvider>
            <ExporterDashboard />
          </ExporterAuthProvider>
        } />
        <Route path="/lcopilot/combined-dashboard" element={
          <ExporterAuthProvider>
            <CombinedDashboard />
          </ExporterAuthProvider>
        } />
        <Route path="/lcopilot/exporter-dashboard/legacy" element={<Navigate to="/lcopilot/exporter-dashboard" replace />} />
        <Route path="/lcopilot/exporter-dashboard/v2" element={<Navigate to="/lcopilot/exporter-dashboard" replace />} />
        <Route path="/lcopilot/importer-dashboard/login" element={
          <ImporterAuthProvider>
            <ImporterLogin />
          </ImporterAuthProvider>
        } />
        <Route path="/lcopilot/importer-dashboard" element={
          <ImporterAuthProvider>
            <ImporterDashboardV2 />
          </ImporterAuthProvider>
        } />
        <Route path="/lcopilot/importer-dashboard/legacy" element={<ImporterDashboard />} />
        <Route path="/lcopilot/enterprise-dashboard" element={
          <ExporterAuthProvider>
            <EnterpriseDashboard />
          </ExporterAuthProvider>
        } />
        <Route path="/lcopilot/exporter-results" element={<ExporterResults />} />
        <Route path="/lcopilot/exporter-analytics" element={<ExporterAnalytics />} />
        <Route path="/lcopilot/importer-analytics" element={<ImporterAnalytics />} />
        <Route path="/lcopilot/analytics" element={<AnalyticsPage />} />
        <Route path="/lcopilot/analytics/exporter" element={<ExporterAnalyticsPage />} />
        <Route path="/lcopilot/analytics/bank" element={<BankAnalyticsPage />} />
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
        <Route path="/lcopilot/exporter-corrections" element={<ExporterDocumentCorrections />} />
        <Route path="/lcopilot/supplier-corrections" element={<SupplierDocumentCorrections />} />
        <Route path="/lcopilot/supplier-results" element={<SupplierDocumentResults />} />
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
