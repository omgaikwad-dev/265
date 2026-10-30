import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  User, 
  ArrowRight, 
  AlertCircle, 
  Building2, 
  CheckCircle, 
  Sparkles,
  Key
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login({ onNavigateToRegister }) {
  const { login, demoAccounts } = useAuth();
  const [identifier, setIdentifier] = useState('inst_admin@fdrsetu.gov.in');
  const [password, setPassword] = useState('Admin@123');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!identifier || !password) {
      setError("Please provide both username/email and password.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await login(identifier, password);
    } catch (err) {
      console.error("Login failed:", err);
      setError(
        err.response?.data?.detail || "Authentication failed. Please verify your credentials."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectDemo = (demo) => {
    setIdentifier(demo.email);
    setPassword(demo.password);
    setError(null);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="max-w-4xl w-full bg-white rounded-2xl shadow-elevated border border-slate-200 overflow-hidden grid grid-cols-1 md:grid-cols-12">
        
        {/* Left Branding Column */}
        <div className="md:col-span-5 bg-gradient-to-br from-primary-dark via-primary to-[#004d73] p-8 text-white flex flex-col justify-between">
          <div className="space-y-6">
            <div className="w-14 h-14 bg-white/10 backdrop-blur-md rounded-xl flex items-center justify-center border border-white/20">
              <ShieldCheck className="w-8 h-8 text-white" />
            </div>
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-widest font-semibold text-blue-200">
                Official AICTE Portal
              </span>
              <h2 className="text-2xl font-bold tracking-tight">FDRSetu</h2>
              <p className="text-xs text-blue-100 leading-relaxed">
                Centralized Fixed Deposit Receipt Verification &amp; Security Deposit Lifecycle Governance System.
              </p>
            </div>
            
            <div className="pt-4 border-t border-white/10 space-y-2.5 text-xs text-blue-100">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-300 flex-shrink-0" />
                <span>AI-Powered Automated OCR Extraction</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-300 flex-shrink-0" />
                <span>12-Rule Intelligent Verification Engine</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-300 flex-shrink-0" />
                <span>Maturity Monitoring &amp; Renewal Reminders</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-300 flex-shrink-0" />
                <span>Immutable Statutory Audit Trail</span>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-white/10 text-[11px] text-blue-200">
            <span>Security Classification: Restricted Government Portal</span>
          </div>
        </div>

        {/* Right Form & Quick-Role Selector Column */}
        <div className="md:col-span-7 p-8 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-xl font-bold text-slate-800">Sign In</h3>
                <p className="text-xs text-slate-500 mt-0.5">Select a role or enter your institutional credentials</p>
              </div>
              <span className="bg-secondary text-primary text-xs font-semibold px-2.5 py-1 rounded-md border border-blue-200">
                Secure Access
              </span>
            </div>

            {/* Error Message Banner */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2.5 text-xs text-danger">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Demo Quick-Select Buttons */}
            <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wide flex items-center space-x-1">
                  <Sparkles className="w-3.5 h-3.5 text-primary" />
                  <span>1-Click Role Switcher (For Demonstration)</span>
                </span>
                <span className="text-[10px] text-slate-400">Select any role below</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {demoAccounts.map((d, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSelectDemo(d)}
                    className={`text-left p-2 rounded-lg border text-xs transition ${
                      identifier === d.email 
                        ? 'bg-blue-50 border-primary text-primary font-semibold shadow-xs' 
                        : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    <div className="font-semibold truncate">{d.role_title || d.role_name}</div>
                    <div className="text-[10px] text-slate-500 truncate">{d.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Credentials Form */}
            <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address / Username
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="username-input"
                    type="text"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    required
                    placeholder="e.g. inst_admin@fdrsetu.gov.in"
                    className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="password-input"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="Enter account password"
                    className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-slate-800"
                  />
                </div>
              </div>

              <button
                id="login-submit-btn"
                type="submit"
                disabled={submitting}
                className="w-full mt-2 bg-primary hover:bg-primary-dark text-white font-semibold text-xs py-2.5 rounded-lg transition shadow-sm flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>{submitting ? 'Authenticating...' : 'Sign In to Portal'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>

          {/* New Institution Onboarding CTA */}
          <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between text-xs">
            <span className="text-slate-500">New Technical Institution?</span>
            <button
              id="navigate-register-btn"
              onClick={onNavigateToRegister}
              className="text-primary hover:text-primary-dark font-semibold inline-flex items-center space-x-1"
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Register Institution</span>
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}
