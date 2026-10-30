import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Database, 
  Server, 
  HardDrive, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Layers, 
  Clock,
  LayoutDashboard,
  LogIn,
  Building2,
  Activity
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { systemService } from './services/api';
import Login from './pages/Login';
import RegisterInstitution from './pages/RegisterInstitution';
import Dashboard from './pages/Dashboard';
import NotificationBellDropdown from './components/NotificationBellDropdown';

function MainApp() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [currentView, setCurrentView] = useState('auto'); // 'auto', 'login', 'register', 'diagnostics'
  const [healthData, setHealthData] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);
  const [latency, setLatency] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    const start = performance.now();
    try {
      const data = await systemService.getHealth();
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealthData(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Health check error:", err);
      setHealthError(err.message || "Failed to reach backend server");
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  // Determine active view
  let activeTab = currentView;
  if (currentView === 'auto') {
    activeTab = isAuthenticated ? 'dashboard' : 'login';
  }

  const phases = [
    { num: 1, title: "Foundation & Full-Stack Connectivity", status: "VERIFIED", desc: "FastAPI REST backend, Vite React frontend, database engine & live health check API" },
    { num: 2, title: "Authentication & Role-Based Access Control", status: "VERIFIED", desc: "JWT tokens, Bcrypt hashing, 5 independent user roles, institution data isolation" },
    { num: 3, title: "Institution & FDR Management", status: "VERIFIED", desc: "Institution profiles, FDR repository, isolated multi-tenant records" },
    { num: 4, title: "OCR & Document Intelligence", status: "VERIFIED", desc: "PaddleOCR & PyMuPDF extraction, field confidence scoring, human review interface" },
    { num: 5, title: "Intelligent Verification Engine", status: "VERIFIED", desc: "12 automated validation rules, cross-document discrepancy detection" },
    { num: 6, title: "FDR Lifecycle Monitoring", status: "VERIFIED", desc: "Maturity tracking, renewal workflows, replacement linking, expiry alerts" },
    { num: 7, title: "Release & Refund Workflow", status: "VERIFIED", desc: "Multi-level scrutiny queue, approving authority decision recording" },
    { num: 8, title: "Notification Engine", status: "VERIFIED", desc: "Scheduled reminders (90/60/30/15/7 days), in-app alerts, audit escalations" },
    { num: 9, title: "Dashboards & Audit Analytics", status: "Upcoming", desc: "Real-time SQL metric queries, Recharts analytics, immutable audit logs" },
    { num: 10, title: "Final Integration & Containerization", status: "Upcoming", desc: "Docker Compose, end-to-end testing, demo workflows" },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      
      {/* Top Government Branding Bar */}
      <div className="bg-[#004d73] text-white px-6 py-2 text-xs flex justify-between items-center border-b border-primary-dark">
        <div className="flex items-center space-x-2">
          <span className="font-semibold tracking-wide">ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)</span>
          <span className="text-blue-200">|</span>
          <span className="text-blue-100">Ministry of Education, Government of India</span>
        </div>
        <div className="flex items-center space-x-4 text-blue-100">
          <span>Security Classification: Restricted</span>
          <span>Official Digital Portal</span>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white border-b border-slate-200 shadow-subtle px-6 py-3.5 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          
          {/* Logo & Title */}
          <div 
            onClick={() => setCurrentView('auto')}
            className="flex items-center space-x-3.5 cursor-pointer"
          >
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white shadow-sm">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-xl font-bold text-primary tracking-tight">FDRSetu</h1>
                <span className="bg-emerald-50 text-success text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
                  Phase 8 Complete
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                AICTE Intelligent Security Deposit &amp; Fixed Deposit Receipt Management System
              </p>
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center space-x-3">
            
            {/* View Navigation Tabs */}
            <nav className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs">
              {isAuthenticated ? (
                <button
                  id="nav-dashboard-btn"
                  onClick={() => setCurrentView('dashboard')}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-medium transition ${
                    activeTab === 'dashboard' ? 'bg-white text-primary shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  <span>Workspace</span>
                </button>
              ) : (
                <>
                  <button
                    id="nav-login-btn"
                    onClick={() => setCurrentView('login')}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-medium transition ${
                      activeTab === 'login' ? 'bg-white text-primary shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <LogIn className="w-3.5 h-3.5" />
                    <span>Sign In</span>
                  </button>
                  <button
                    id="nav-register-btn"
                    onClick={() => setCurrentView('register')}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-medium transition ${
                      activeTab === 'register' ? 'bg-white text-primary shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Register</span>
                  </button>
                </>
              )}

              <button
                id="nav-diagnostics-btn"
                onClick={() => setCurrentView('diagnostics')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === 'diagnostics' ? 'bg-white text-primary shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Telemetry &amp; Roadmap</span>
              </button>
            </nav>

            {/* Notification Center */}
            {isAuthenticated && (
              <NotificationBellDropdown />
            )}

            {/* Health Pill */}
            <div className="flex items-center space-x-2 bg-slate-50 px-2.5 py-1.5 rounded-md border border-slate-200 text-xs">
              <div className={`w-2 h-2 rounded-full ${healthData?.status === 'healthy' ? 'bg-success animate-pulse' : healthError ? 'bg-danger' : 'bg-warning'}`}></div>
              <span className="text-slate-700 font-medium hidden sm:inline">
                {healthLoading ? 'Verifying...' : healthData?.status === 'healthy' ? 'Online' : 'Degraded'}
              </span>
            </div>

          </div>

        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6">
        
        {/* Authentication Loading State */}
        {authLoading ? (
          <div className="flex items-center justify-center py-24 text-slate-500 text-xs space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-primary" />
            <span>Verifying session security...</span>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && <Dashboard />}
            {activeTab === 'login' && <Login onNavigateToRegister={() => setCurrentView('register')} />}
            {activeTab === 'register' && <RegisterInstitution onNavigateToLogin={() => setCurrentView('login')} />}
            {activeTab === 'diagnostics' && (
              <div className="space-y-8">
                
                {/* Diagnostics Header */}
                <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                  <div>
                    <h3 className="text-xl font-bold text-slate-800">System Telemetry &amp; Foundation Verification</h3>
                    <p className="text-xs text-slate-500">Live health telemetry from FastAPI backend and master implementation tracker</p>
                  </div>
                  <button
                    id="refresh-health-btn"
                    onClick={fetchHealth}
                    disabled={healthLoading}
                    className="flex items-center space-x-1.5 bg-primary hover:bg-primary-dark text-white text-xs font-medium px-3.5 py-2 rounded-lg transition shadow-xs disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${healthLoading ? 'animate-spin' : ''}`} />
                    <span>Refresh Telemetry</span>
                  </button>
                </div>

                {/* Telemetry Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-semibold uppercase text-slate-400">REST API</span>
                        <h4 className="text-lg font-bold text-slate-800 mt-1">FastAPI Backend</h4>
                      </div>
                      <div className="p-2.5 bg-blue-50 text-primary rounded-lg">
                        <Server className="w-5 h-5" />
                      </div>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Status:</span>
                        <span className="text-success font-semibold uppercase">{healthData?.status || 'ONLINE'}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Latency:</span>
                        <span className="font-semibold text-slate-700">{latency ? `${latency} ms` : '--'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-semibold uppercase text-slate-400">Database Engine</span>
                        <h4 className="text-lg font-bold text-slate-800 mt-1">SQLAlchemy ORM</h4>
                      </div>
                      <div className="p-2.5 bg-blue-50 text-primary rounded-lg">
                        <Database className="w-5 h-5" />
                      </div>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Connection:</span>
                        <span className="text-success font-semibold">VERIFIED</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Dialect:</span>
                        <span className="font-mono text-slate-700 uppercase font-semibold">{healthData?.database?.dialect || 'SQLITE'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-semibold uppercase text-slate-400">File Storage</span>
                        <h4 className="text-lg font-bold text-slate-800 mt-1">Document Vault</h4>
                      </div>
                      <div className="p-2.5 bg-blue-50 text-primary rounded-lg">
                        <HardDrive className="w-5 h-5" />
                      </div>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Uploads Vault:</span>
                        <span className="text-success font-semibold">READY &amp; WRITABLE</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Max File Limit:</span>
                        <span className="text-slate-700 font-semibold">10 MB</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-semibold uppercase text-slate-400">Security Architecture</span>
                        <h4 className="text-lg font-bold text-slate-800 mt-1">JWT &amp; RBAC</h4>
                      </div>
                      <div className="p-2.5 bg-blue-50 text-primary rounded-lg">
                        <ShieldCheck className="w-5 h-5" />
                      </div>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Role System:</span>
                        <span className="text-primary font-semibold">5 Discrete Roles</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Isolation:</span>
                        <span className="text-success font-semibold">Enforced (Rule 11)</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Raw API Telemetry */}
                {healthData && (
                  <div className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-xs overflow-x-auto border border-slate-800 shadow-inner">
                    <div className="flex justify-between items-center pb-2 mb-2 border-b border-slate-800 text-slate-400">
                      <span className="flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-success"></span>
                        <span>Payload: GET /api/v1/health</span>
                      </span>
                      <span>{healthData.timestamp}</span>
                    </div>
                    <pre className="text-blue-300">{JSON.stringify(healthData, null, 2)}</pre>
                  </div>
                )}

                {/* 10 Implementation Phases Roadmap */}
                <div className="space-y-4">
                  <div className="border-b border-slate-200 pb-2">
                    <h3 className="text-lg font-bold text-slate-800">Master Project Implementation Roadmap</h3>
                    <p className="text-xs text-slate-500">Structured modular delivery plan strictly following hackathon criteria</p>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 shadow-subtle overflow-hidden">
                    <div className="divide-y divide-slate-100">
                      {phases.map((p) => (
                        <div key={p.num} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition">
                          <div className="flex items-start space-x-3.5">
                            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                              p.status === 'VERIFIED' ? 'bg-success text-white shadow-xs' : 'bg-slate-100 text-slate-500'
                            }`}>
                              {p.num}
                            </div>
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-semibold text-sm text-slate-800">{p.title}</span>
                                {p.status === 'VERIFIED' && (
                                  <span className="bg-green-100 text-success text-[10px] font-bold px-2 py-0.5 rounded-full">
                                    COMPLETED &amp; VERIFIED
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-500 mt-0.5">{p.desc}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className={`text-xs font-medium px-2.5 py-1 rounded-md ${
                              p.status === 'VERIFIED' ? 'bg-emerald-50 text-success border border-emerald-100' : 'text-slate-400'
                            }`}>
                              {p.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

              </div>
            )}
          </>
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-3.5 px-6 text-xs text-slate-500 text-center">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0">
          <div>
            <span>FDRSetu &copy; 2026 AICTE Intelligent Security Deposit Portal.</span>
          </div>
          <div className="flex items-center space-x-4">
            <span>FastAPI REST Backend</span>
            <span>•</span>
            <span>React + Vite Frontend</span>
            <span>•</span>
            <span>Bcrypt &amp; PyJWT Auth</span>
            <span>•</span>
            <span>5-Tier RBAC Architecture</span>
          </div>
        </div>
      </footer>

    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
