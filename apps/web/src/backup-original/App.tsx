import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/landing/LandingPage'
import WelcomePage from './pages/WelcomePage'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import ReportPage from './pages/ReportPage'
import ToolsPage from './pages/ToolsPage'
import PricingPage from './pages/PricingPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import Login from './pages/Login'
import Register from './pages/Register'
import StubModeIndicator from './components/StubModeIndicator'
import DiscrepancyListDemo from './components/DiscrepancyListDemo'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/lcopilot" element={<WelcomePage />} />
        <Route path="/lcopilot/login" element={<Login />} />
        <Route path="/lcopilot/register" element={<Register />} />
        <Route path="/lcopilot/upload" element={<UploadPage />} />
        <Route path="/lcopilot/review/:sessionId" element={<ReviewPage />} />
        <Route path="/lcopilot/report/:sessionId" element={<ReportPage />} />
        <Route path="/lcopilot/demo" element={<DiscrepancyListDemo />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <StubModeIndicator />
    </>
  )
}

export default App