import { Routes, Route } from 'react-router-dom'
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
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import UploadLC from './pages/UploadLC'
import Results from './pages/Results'
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
import AdminDashboard from './pages/admin/AdminDashboard'
import { Toaster } from './components/ui/toaster'

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
        <Route path="/lcopilot" element={<Index />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/lcopilot/upload" element={<UploadPage />} />
        <Route path="/lcopilot/review/:sessionId" element={<ReviewPage />} />
        <Route path="/lcopilot/report/:sessionId" element={<ReportPage />} />
        <Route path="/lcopilot/demo" element={<DiscrepancyListDemo />} />
        <Route path="/lcopilot/dashboard" element={<Dashboard />} />
        <Route path="/lcopilot/upload-lc" element={<UploadLC />} />
        <Route path="/lcopilot/results" element={<Results />} />
        <Route path="/lcopilot/results/:jobId" element={<Results />} />
        <Route path="/lcopilot/draft-corrections" element={<DraftLCCorrections />} />
        <Route path="/lcopilot/draft-risk-results" element={<DraftLCRiskResults />} />
        <Route path="/export-lc-upload" element={<ExportLCUpload />} />
        <Route path="/lcopilot/import-upload" element={<ImportLCUpload />} />
        <Route path="/import/results/:jobId" element={<ImportResults />} />
        <Route path="/lcopilot/import-results/:jobId" element={<ImportResults />} />
        <Route path="/lcopilot/exporter-dashboard" element={<ExporterDashboard />} />
        <Route path="/lcopilot/importer-dashboard" element={<ImporterDashboard />} />
        <Route path="/lcopilot/exporter-results" element={<ExporterResults />} />
        <Route path="/lcopilot/exporter-analytics" element={<ExporterAnalytics />} />
        <Route path="/lcopilot/importer-analytics" element={<ImporterAnalytics />} />
        <Route path="/lcopilot/analytics" element={<AnalyticsPage />} />
        <Route path="/lcopilot/analytics/exporter" element={<ExporterAnalyticsPage />} />
        <Route path="/lcopilot/analytics/bank" element={<BankAnalyticsPage />} />
        <Route path="/lcopilot/bank-dashboard" element={<BankDashboard />} />
        <Route path="/lcopilot/bank-dashboard/v2" element={<BankDashboardV2 />} />
        <Route path="/lcopilot/bank-dashboard/client/:clientName" element={<ClientDashboard />} />
        <Route path="/lcopilot/component-gallery" element={<ComponentGallery />} />
        <Route path="/lcopilot/exporter-corrections" element={<ExporterDocumentCorrections />} />
        <Route path="/lcopilot/supplier-corrections" element={<SupplierDocumentCorrections />} />
        <Route path="/lcopilot/supplier-results" element={<SupplierDocumentResults />} />
        <Route path="/test-import" element={<ImportResultsSimple />} />
        <Route path="/lcopilot/support" element={<Support />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <StubModeIndicator />

    </>
  )
}

export default App
