import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  ShieldCheck, 
  CheckCircle2, 
  FileText, 
  Search, 
  RefreshCw, 
  AlertTriangle, 
  Sliders, 
  History, 
  UserCheck, 
  Eye, 
  Download, 
  Bell, 
  Plus,
  ArrowUpRight,
  LogOut,
  Sparkles,
  Lock,
  Filter
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { institutionService, fdrService, lifecycleService, releaseService } from '../services/api';
import NewFDRModal from '../components/NewFDRModal';
import FDRDetailModal from '../components/FDRDetailModal';
import OCRReviewModal from '../components/OCRReviewModal';
import VerificationReportModal from '../components/VerificationReportModal';
import InitiateRenewalModal from '../components/InitiateRenewalModal';
import RequestReleaseModal from '../components/RequestReleaseModal';
import AuthorityDecisionModal from '../components/AuthorityDecisionModal';

export default function Dashboard() {
  const { user, role, logout, login, demoAccounts } = useAuth();
  
  // Data states
  const [fdrs, setFdrs] = useState([]);
  const [loadingFdrs, setLoadingFdrs] = useState(false);
  const [institutions, setInstitutions] = useState([]);
  const [loadingInstitutions, setLoadingInstitutions] = useState(false);
  const [approvalQueue, setApprovalQueue] = useState({ pending_scrutiny_fdrs: [], pending_releases: [] });
  const [loadingQueue, setLoadingQueue] = useState(false);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [bankFilter, setBankFilter] = useState('');

  // Modal states
  const [isNewFDRModalOpen, setIsNewFDRModalOpen] = useState(false);
  const [selectedFDR, setSelectedFDR] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isOCRModalOpen, setIsOCRModalOpen] = useState(false);
  const [ocrTargetFDR, setOcrTargetFDR] = useState(null);
  const [isVerificationModalOpen, setIsVerificationModalOpen] = useState(false);
  const [verificationTargetFDR, setVerificationTargetFDR] = useState(null);
  const [isRenewalModalOpen, setIsRenewalModalOpen] = useState(false);
  const [renewalTargetFDR, setRenewalTargetFDR] = useState(null);
  const [isReleaseModalOpen, setIsReleaseModalOpen] = useState(false);
  const [releaseTargetFDR, setReleaseTargetFDR] = useState(null);
  const [isAuthorityModalOpen, setIsAuthorityModalOpen] = useState(false);
  const [authorityTargetItem, setAuthorityTargetItem] = useState(null);
  const [authorityTargetType, setAuthorityTargetType] = useState('FDR');
  const [scanningMaturity, setScanningMaturity] = useState(false);
  const [switchingRole, setSwitchingRole] = useState(false);

  useEffect(() => {
    fetchFDRs();
    if (role === 'ROLE_SYSTEM_ADMIN') {
      fetchInstitutions();
    }
    if (role === 'ROLE_APPROVING_AUTHORITY') {
      fetchApprovalQueue();
    }
  }, [role, statusFilter, bankFilter]);

  const fetchApprovalQueue = async () => {
    setLoadingQueue(true);
    try {
      const q = await releaseService.getApprovalQueue();
      setApprovalQueue(q);
    } catch (e) {
      console.error("Failed to load approval queue:", e);
    } finally {
      setLoadingQueue(false);
    }
  };

  const handleOpenRequestRelease = (fdrItem) => {
    setReleaseTargetFDR(fdrItem);
    setIsReleaseModalOpen(true);
  };

  const handleOpenAuthorityDecision = (targetItem, targetType = 'FDR') => {
    setAuthorityTargetItem(targetItem);
    setAuthorityTargetType(targetType);
    setIsAuthorityModalOpen(true);
  };

  const fetchFDRs = async () => {
    setLoadingFdrs(true);
    try {
      const data = await fdrService.getAll({
        status: statusFilter || undefined,
        bank: bankFilter || undefined,
        search: searchQuery || undefined
      });
      setFdrs(data);
    } catch (err) {
      console.error("Failed to fetch FDRs:", err);
    } finally {
      setLoadingFdrs(false);
    }
  };

  const fetchInstitutions = async () => {
    setLoadingInstitutions(true);
    try {
      const data = await institutionService.getAll();
      setInstitutions(data);
    } catch (err) {
      console.error("Failed to fetch institutions:", err);
    } finally {
      setLoadingInstitutions(false);
    }
  };

  const handleQuickSwitch = async (demo) => {
    setSwitchingRole(true);
    try {
      await login(demo.email, demo.password);
    } catch (e) {
      console.error("Role switch error:", e);
    } finally {
      setSwitchingRole(false);
    }
  };

  const handleOpenDetail = (fdrItem) => {
    setSelectedFDR(fdrItem);
    setIsDetailModalOpen(true);
  };

  const handleOpenOCR = (fdrItem) => {
    setOcrTargetFDR(fdrItem);
    setIsOCRModalOpen(true);
  };

  const handleOpenVerification = (fdrItem) => {
    setVerificationTargetFDR(fdrItem);
    setIsVerificationModalOpen(true);
  };

  const handleOpenRenewal = (fdrItem) => {
    setRenewalTargetFDR(fdrItem);
    setIsRenewalModalOpen(true);
  };

  const handleTriggerMaturityScan = async () => {
    setScanningMaturity(true);
    try {
      const res = await lifecycleService.scanMaturities();
      alert(`Maturity scan completed!\nTotal Monitored: ${res.total_scanned}\nFlagged as Matured: ${res.matured_count}\nFlagged as Renewal Due: ${res.renewal_due_count}`);
      fetchFDRs();
    } catch (e) {
      console.error("Scan error:", e);
      alert("Failed to execute maturity scan.");
    } finally {
      setScanningMaturity(false);
    }
  };

  // Metrics derived from live database records
  const totalDepositAmount = fdrs
    .filter(f => f.lifecycle_status === 'APPROVED_ACTIVE' || f.lifecycle_status === 'UNDER_SCRUTINY')
    .reduce((sum, f) => sum + parseFloat(f.deposit_amount || 0), 0);

  const activeCount = fdrs.filter(f => f.lifecycle_status === 'APPROVED_ACTIVE').length;
  const underScrutinyCount = fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').length;
  const draftCount = fdrs.filter(f => f.lifecycle_status === 'DRAFT').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED_ACTIVE':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'UNDER_SCRUTINY':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'DRAFT':
        return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'RENEWAL_DUE':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MATURED':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      default:
        return 'bg-blue-100 text-primary border-blue-200';
    }
  };

  const getRoleDetails = (roleName) => {
    switch (roleName) {
      case 'ROLE_INSTITUTION_ADMIN':
        return { label: 'Institution Admin (Role 1)', bg: 'bg-blue-100 text-primary border-blue-200' };
      case 'ROLE_SCRUTINY_OFFICER':
        return { label: 'Scrutiny Officer (Role 2)', bg: 'bg-amber-100 text-amber-800 border-amber-200' };
      case 'ROLE_APPROVING_AUTHORITY':
        return { label: 'Approving Authority (Role 3)', bg: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
      case 'ROLE_SYSTEM_ADMIN':
        return { label: 'System Admin (Role 4)', bg: 'bg-purple-100 text-purple-800 border-purple-200' };
      case 'ROLE_AUDITOR':
        return { label: 'Auditor (Role 5)', bg: 'bg-rose-100 text-rose-800 border-rose-200' };
      default:
        return { label: roleName || 'User', bg: 'bg-slate-100 text-slate-800 border-slate-200' };
    }
  };

  const roleMeta = getRoleDetails(role);

  return (
    <div className="space-y-6">
      
      {/* Top Profile & Role Switching Ribbon */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="w-11 h-11 bg-primary text-white rounded-lg flex items-center justify-center font-bold text-sm shadow-sm">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-800">{user?.full_name}</h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${roleMeta.bg}`}>
                {roleMeta.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {user?.designation || 'Authorized Officer'} • {user?.email}
              {user?.institution && ` • Institution: ${user.institution.name} (${user.institution.aicte_id})`}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Quick Demo Switcher Dropdown */}
          <div className="relative group">
            <button
              id="switch-role-menu-btn"
              disabled={switchingRole}
              className="flex items-center space-x-1.5 text-xs bg-secondary hover:bg-secondary-hover text-primary font-medium px-3 py-2 rounded-lg border border-blue-200 transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{switchingRole ? 'Switching...' : 'Switch Role (1-Click)'}</span>
            </button>
            <div className="absolute right-0 mt-1 w-64 bg-white border border-slate-200 rounded-xl shadow-elevated p-2 hidden group-hover:block z-50">
              <div className="text-[10px] uppercase font-bold text-slate-400 px-2 py-1">Quick Switch Role</div>
              {demoAccounts.map((d, i) => (
                <button
                  key={i}
                  onClick={() => handleQuickSwitch(d)}
                  className={`w-full text-left p-2 rounded-lg text-xs transition flex flex-col ${
                    d.email === user?.email ? 'bg-blue-50 font-bold text-primary' : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <span className="truncate">{d.role_title}</span>
                  <span className="text-[10px] text-slate-400 truncate">{d.name}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            id="logout-btn"
            onClick={logout}
            className="flex items-center space-x-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-3 py-2 rounded-lg transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* =========================================================================
          ROLE 1 WORKSPACE: INSTITUTION ADMINISTRATOR
          ========================================================================= */}
      {role === 'ROLE_INSTITUTION_ADMIN' && (
        <div className="space-y-6">
          
          {/* Institution Header Banner */}
          <div className="bg-gradient-to-r from-primary to-[#005580] rounded-xl p-6 text-white shadow-card">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="inline-flex items-center space-x-1.5 bg-white/10 px-2.5 py-0.5 rounded-full text-xs text-blue-100 mb-2">
                  <Building2 className="w-3.5 h-3.5" />
                  <span>AICTE Approved Institution Workspace</span>
                </div>
                <h3 className="text-xl font-bold">{user?.institution?.name || "Institution Repository"}</h3>
                <p className="text-xs text-blue-100 mt-1">
                  Permanent AICTE ID: <span className="font-mono font-semibold">{user?.institution?.aicte_id}</span> • State: {user?.institution?.state} • Status: <span className="font-semibold text-emerald-300">{user?.institution?.account_status}</span>
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  id="open-new-fdr-modal-btn"
                  onClick={() => setIsNewFDRModalOpen(true)}
                  className="bg-white hover:bg-blue-50 text-primary font-bold text-xs px-4 py-2.5 rounded-lg transition shadow-md flex items-center space-x-1.5"
                >
                  <Plus className="w-4 h-4" />
                  <span>Submit New FDR</span>
                </button>
              </div>
            </div>
          </div>

          {/* Database-Driven Real-Time Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle hover:border-primary/40 transition">
              <span className="text-xs font-semibold uppercase text-slate-400">Total FDR Deposit Value</span>
              <h4 className="text-2xl font-bold text-slate-800 mt-1">
                ₹ {totalDepositAmount.toLocaleString('en-IN')}
              </h4>
              <p className="text-xs text-slate-500 mt-2">Active &amp; submitted instruments</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle hover:border-primary/40 transition">
              <span className="text-xs font-semibold uppercase text-slate-400">Active Instruments</span>
              <h4 className="text-2xl font-bold text-success mt-1">{activeCount} Approved</h4>
              <p className="text-xs text-slate-500 mt-2">Verified by AICTE Scrutiny</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle hover:border-primary/40 transition">
              <span className="text-xs font-semibold uppercase text-slate-400">Under Scrutiny</span>
              <h4 className="text-2xl font-bold text-amber-700 mt-1">{underScrutinyCount} Pending</h4>
              <p className="text-xs text-slate-500 mt-2">In AICTE examination queue</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle hover:border-primary/40 transition">
              <span className="text-xs font-semibold uppercase text-slate-400">Drafts / Incomplete</span>
              <h4 className="text-2xl font-bold text-slate-600 mt-1">{draftCount} Drafts</h4>
              <p className="text-xs text-slate-500 mt-2">Requires document attachment</p>
            </div>
          </div>

          {/* Live Institutional FDR Repository Data Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-subtle overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Submitted Security Deposits &amp; Fixed Deposits</h4>
                <p className="text-xs text-slate-500">Live database records for this institution ({fdrs.length} total instruments)</p>
              </div>

              {/* Filters & Actions */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && fetchFDRs()}
                    placeholder="Search FDR number..."
                    className="text-xs pl-8 pr-3 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary w-40"
                  />
                </div>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Statuses</option>
                  <option value="APPROVED_ACTIVE">Approved Active</option>
                  <option value="UNDER_SCRUTINY">Under Scrutiny</option>
                  <option value="DRAFT">Draft</option>
                  <option value="RENEWAL_DUE">Renewal Due</option>
                </select>

                <button
                  onClick={fetchFDRs}
                  className="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-600 transition"
                  title="Refresh Table"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingFdrs ? 'animate-spin' : ''}`} />
                </button>

                <button 
                  id="add-fdr-table-btn"
                  onClick={() => setIsNewFDRModalOpen(true)}
                  className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition shadow-xs flex items-center space-x-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>New FDR</span>
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">FDR Number</th>
                    <th className="px-4 py-3">Issuing Bank</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Issue Date</th>
                    <th className="px-4 py-3">Maturity Date</th>
                    <th className="px-4 py-3">Docs</th>
                    <th className="px-4 py-3">OCR Status</th>
                    <th className="px-4 py-3">Verification</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fdrs.map((item) => (
                    <tr 
                      key={item.id} 
                      onClick={() => handleOpenDetail(item)}
                      className="hover:bg-blue-50/30 transition cursor-pointer"
                    >
                      <td className="px-4 py-3 font-mono font-bold text-primary">{item.fdr_number}</td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-800">{item.bank_name}</div>
                        <div className="text-[10px] text-slate-400">{item.branch_name}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-800">
                        ₹ {Number(item.deposit_amount).toLocaleString('en-IN')}
                      </td>
                      <td className="px-4 py-3 font-mono">{item.issue_date}</td>
                      <td className="px-4 py-3 font-mono">{item.maturity_date}</td>
                      <td className="px-4 py-3 font-semibold">
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px]">
                          {item.documents?.length || 0} files
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="bg-blue-50 text-primary px-2 py-0.5 rounded font-semibold text-[10px] uppercase">
                          {item.ocr_status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="bg-emerald-50 text-success px-2 py-0.5 rounded font-semibold text-[10px] uppercase">
                          {item.verification_status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2.5 py-0.5 rounded-full font-bold text-[10px] border ${getStatusBadge(item.lifecycle_status)}`}>
                          {item.lifecycle_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleOpenOCR(item); }}
                            className="bg-blue-50 hover:bg-blue-100 text-primary font-semibold text-[11px] px-2 py-1 rounded transition flex items-center space-x-1"
                            title="AI OCR Review & Extraction"
                          >
                            <Sparkles className="w-3 h-3 text-primary" />
                            <span>OCR</span>
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleOpenVerification(item); }}
                            className="bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-[11px] px-2 py-1 rounded transition flex items-center space-x-1"
                            title="12-Rule Verification Report"
                          >
                            <ShieldCheck className="w-3 h-3 text-amber-700" />
                            <span>Verify</span>
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleOpenDetail(item); }}
                            className="text-slate-600 hover:text-slate-900 font-semibold text-xs inline-flex items-center space-x-1 px-1.5 py-1"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>View</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {fdrs.length === 0 && (
                    <tr>
                      <td colSpan="10" className="px-4 py-8 text-center text-slate-400">
                        {loadingFdrs ? 'Loading FDR records...' : 'No FDR instruments on record. Click "+ Submit New FDR" to add your first security deposit.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          ROLE 2 WORKSPACE: AICTE SCRUTINY OFFICER
          ========================================================================= */}
      {role === 'ROLE_SCRUTINY_OFFICER' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-amber-700 to-amber-900 rounded-xl p-6 text-white shadow-card flex justify-between items-center">
            <div>
              <h3 className="text-xl font-bold">AICTE Scrutiny &amp; Verification Desk</h3>
              <p className="text-xs text-amber-100 mt-1">
                Examine submitted FDR instruments across all technical institutions against AI-OCR extractions and bank records.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleTriggerMaturityScan}
                disabled={scanningMaturity}
                className="bg-white/10 hover:bg-white/20 text-white font-semibold text-xs px-3 py-1.5 rounded-lg border border-white/20 transition flex items-center space-x-1.5"
                title="Execute automated maturity scan across database"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${scanningMaturity ? 'animate-spin' : ''}`} />
                <span>{scanningMaturity ? 'Scanning...' : 'Scan Maturities'}</span>
              </button>
              <span className="bg-white/10 px-3 py-1 rounded-full text-xs font-semibold">
                {fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').length} Cases Pending
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Scrutiny Queue</span>
              <h4 className="text-2xl font-bold text-amber-700 mt-1">
                {fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').length} Under Examination
              </h4>
              <p className="text-xs text-slate-500 mt-2">Awaiting officer observations</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Approved Active</span>
              <h4 className="text-2xl font-bold text-success mt-1">{activeCount} Approved</h4>
              <p className="text-xs text-slate-500 mt-2">Verified instruments</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Total Scrutiny Dossiers</span>
              <h4 className="text-2xl font-bold text-slate-800 mt-1">{fdrs.length} Records</h4>
              <p className="text-xs text-slate-500 mt-2">Across all institutions</p>
            </div>
          </div>

          {/* Scrutiny Queue Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-subtle overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Scrutiny Examination Queue</h4>
                <p className="text-xs text-slate-500">Click any dossier to examine OCR extracted fields and supporting documents</p>
              </div>
              <button onClick={fetchFDRs} className="p-1.5 bg-slate-100 rounded-lg text-slate-600">
                <RefreshCw className={`w-3.5 h-3.5 ${loadingFdrs ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">FDR Number</th>
                    <th className="px-4 py-3">Institution Name</th>
                    <th className="px-4 py-3">Bank &amp; Branch</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Maturity Date</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fdrs.map((item) => (
                    <tr key={item.id} onClick={() => handleOpenDetail(item)} className="hover:bg-slate-50 cursor-pointer">
                      <td className="px-4 py-3 font-mono font-bold text-primary">{item.fdr_number}</td>
                      <td className="px-4 py-3 font-semibold text-slate-800">{item.institution_name || 'Delhi Institute of Tech'}</td>
                      <td className="px-4 py-3">{item.bank_name} ({item.branch_name})</td>
                      <td className="px-4 py-3 font-semibold text-slate-800">₹ {Number(item.deposit_amount).toLocaleString('en-IN')}</td>
                      <td className="px-4 py-3 font-mono">{item.maturity_date}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2.5 py-0.5 rounded-full font-bold text-[10px] border ${getStatusBadge(item.lifecycle_status)}`}>
                          {item.lifecycle_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleOpenOCR(item); }}
                            className="bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-[11px] px-2 py-1 rounded transition flex items-center space-x-1"
                            title="Inspect AI OCR Data & Evidence"
                          >
                            <Sparkles className="w-3 h-3 text-amber-600" />
                            <span>AI OCR</span>
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleOpenVerification(item); }}
                            className="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-semibold text-[11px] px-2 py-1 rounded transition flex items-center space-x-1"
                            title="12-Rule Verification Engine & Scrutiny"
                          >
                            <ShieldCheck className="w-3 h-3 text-emerald-700" />
                            <span>12 Rules</span>
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleOpenDetail(item); }}
                            className="text-amber-700 hover:text-amber-900 font-semibold text-xs flex items-center space-x-1"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Examine</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          ROLE 3 WORKSPACE: AICTE APPROVING AUTHORITY
          ========================================================================= */}
      {role === 'ROLE_APPROVING_AUTHORITY' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-emerald-800 to-teal-900 rounded-xl p-6 text-white shadow-card flex justify-between items-center">
            <div>
              <h3 className="text-xl font-bold">AICTE Competent Approving Authority Executive Desk</h3>
              <p className="text-xs text-emerald-100 mt-1">
                Final statutory approval and sign-off on scrutinized FDR instruments, renewals, and release/refund petitions.
              </p>
            </div>
            <button
              onClick={() => { fetchFDRs(); fetchApprovalQueue(); }}
              className="bg-white/10 hover:bg-white/20 text-white font-semibold text-xs px-3 py-1.5 rounded-lg border border-white/20 transition flex items-center space-x-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingQueue ? 'animate-spin' : ''}`} />
              <span>Refresh Queue</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Scrutiny Cases Awaiting Sign-off</span>
              <h4 className="text-2xl font-bold text-amber-700 mt-1">
                {fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').length} Cases
              </h4>
              <p className="text-xs text-slate-500 mt-2">Ready for statutory approval</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Release / Refund Petitions</span>
              <h4 className="text-2xl font-bold text-primary mt-1">
                {approvalQueue.pending_releases?.length || 0} Petitions
              </h4>
              <p className="text-xs text-slate-500 mt-2">Awaiting deposit release authorization</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Total Statutory Custody</span>
              <h4 className="text-2xl font-bold text-emerald-700 mt-1">₹ {totalDepositAmount.toLocaleString('en-IN')}</h4>
              <p className="text-xs text-slate-500 mt-2">{activeCount} Approved active instruments</p>
            </div>
          </div>

          {/* Section A: Scrutiny Approval Queue */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-subtle overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Scrutinized Instruments Awaiting Statutory Approval</h4>
                <p className="text-xs text-slate-500">Examine officer recommendations and grant official AICTE approval or rejection</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">FDR Number</th>
                    <th className="px-4 py-3">Bank &amp; Branch</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Scrutiny Findings &amp; Recommendation</th>
                    <th className="px-4 py-3 text-right">Statutory Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono font-bold text-primary">{item.fdr_number}</td>
                      <td className="px-4 py-3">{item.bank_name} ({item.branch_name})</td>
                      <td className="px-4 py-3 font-semibold text-slate-800">₹ {Number(item.deposit_amount).toLocaleString('en-IN')}</td>
                      <td className="px-4 py-3">
                        <span className="text-slate-700 font-medium">
                          {item.scrutiny_remarks || 'Awaiting officer scrutiny findings'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => handleOpenVerification(item)}
                            className="bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-[11px] px-2 py-1 rounded transition"
                          >
                            Inspect Dossier
                          </button>
                          <button
                            onClick={() => handleOpenAuthorityDecision(item, 'FDR')}
                            className="bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs px-3 py-1.5 rounded-lg transition shadow-xs"
                          >
                            Sign-Off Decision
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {fdrs.filter(f => f.lifecycle_status === 'UNDER_SCRUTINY').length === 0 && (
                    <tr>
                      <td colSpan="5" className="px-4 py-6 text-center text-slate-400">
                        No scrutiny cases awaiting Approving Authority sign-off at this time.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section B: Security Deposit Release & Refund Petitions Queue */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-subtle overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Security Deposit Release &amp; Refund Petitions</h4>
                <p className="text-xs text-slate-500">Petitions submitted by institutions for release of matured or authorized deposits</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Petition ID</th>
                    <th className="px-4 py-3">FDR Reference</th>
                    <th className="px-4 py-3">Refund Account Details</th>
                    <th className="px-4 py-3">Legal Justification</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Statutory Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {approvalQueue.pending_releases?.map((rel) => (
                    <tr key={rel.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono font-bold text-slate-700">#{rel.id}</td>
                      <td className="px-4 py-3 font-mono text-primary font-bold">FDR #{rel.fdr_id}</td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-800">{rel.refund_beneficiary_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {rel.refund_bank_name} • {rel.refund_account_number} (IFSC: {rel.refund_ifsc})
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{rel.release_reason}</td>
                      <td className="px-4 py-3">
                        <span className="bg-amber-100 text-amber-800 font-bold px-2.5 py-0.5 rounded-full text-[10px] uppercase">
                          {rel.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleOpenAuthorityDecision(rel, 'RELEASE')}
                          className="bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs px-3 py-1.5 rounded-lg transition shadow-xs"
                        >
                          Authorize Release
                        </button>
                      </td>
                    </tr>
                  ))}
                  {(!approvalQueue.pending_releases || approvalQueue.pending_releases.length === 0) && (
                    <tr>
                      <td colSpan="6" className="px-4 py-6 text-center text-slate-400">
                        No pending release/refund petitions awaiting authority authorization.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* =========================================================================
          ROLE 4 WORKSPACE: SYSTEM ADMINISTRATOR
          ========================================================================= */}
      {role === 'ROLE_SYSTEM_ADMIN' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-purple-800 to-indigo-900 rounded-xl p-6 text-white shadow-card">
            <h3 className="text-xl font-bold">System Administration &amp; Governance Center</h3>
            <p className="text-xs text-purple-100 mt-1">
              Manage institution onboardings, configure 12-rule verification engine thresholds, and maintain platform security.
            </p>
          </div>

          {/* Live Institution Directory Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-subtle overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Registered Institutions Directory</h4>
                <p className="text-xs text-slate-500">Live database query of institutions onboarded to the AICTE portal</p>
              </div>
              <button onClick={fetchInstitutions} className="p-1.5 bg-slate-100 rounded-lg text-slate-600">
                <RefreshCw className={`w-3.5 h-3.5 ${loadingInstitutions ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">AICTE ID</th>
                    <th className="px-4 py-3">Institution Name</th>
                    <th className="px-4 py-3">State</th>
                    <th className="px-4 py-3">Official Email</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {institutions.map(inst => (
                    <tr key={inst.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-mono font-bold text-primary">{inst.aicte_id}</td>
                      <td className="px-4 py-3 font-semibold text-slate-800">{inst.name}</td>
                      <td className="px-4 py-3">{inst.state}</td>
                      <td className="px-4 py-3 font-mono text-[11px]">{inst.official_email}</td>
                      <td className="px-4 py-3">
                        <span className="bg-emerald-50 text-success border border-emerald-200 px-2.5 py-0.5 rounded-full font-bold text-[10px]">
                          {inst.account_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          ROLE 5 WORKSPACE: AUDITOR
          ========================================================================= */}
      {role === 'ROLE_AUDITOR' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-rose-900 to-slate-900 rounded-xl p-6 text-white shadow-card">
            <h3 className="text-xl font-bold">Statutory &amp; Regulatory Audit Console</h3>
            <p className="text-xs text-rose-100 mt-1">
              Read-only immutable examination of all transactions, verification reports, approval timestamps, and system logs.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Total Monitored Deposits</span>
              <h4 className="text-2xl font-bold text-slate-800 mt-1">{fdrs.length} FDRs</h4>
              <p className="text-xs text-slate-500 mt-2">Under continuous regulatory audit</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Total Inspected Value</span>
              <h4 className="text-2xl font-bold text-success mt-1">₹ {totalDepositAmount.toLocaleString('en-IN')}</h4>
              <p className="text-xs text-slate-500 mt-2">Active security commitments</p>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-subtle">
              <span className="text-xs font-semibold uppercase text-slate-400">Verification Compliance</span>
              <h4 className="text-2xl font-bold text-primary mt-1">100% Inspected</h4>
              <p className="text-xs text-slate-500 mt-2">Immutable audit logs active</p>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <NewFDRModal
        isOpen={isNewFDRModalOpen}
        onClose={() => setIsNewFDRModalOpen(false)}
        onSuccess={() => {
          fetchFDRs();
        }}
      />

      <FDRDetailModal
        fdr={selectedFDR}
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        onOpenOCR={handleOpenOCR}
        onOpenVerification={handleOpenVerification}
        onOpenRenewal={handleOpenRenewal}
        onOpenRelease={handleOpenRequestRelease}
        onRefresh={() => {
          fetchFDRs();
          if (selectedFDR) {
            fdrService.getById(selectedFDR.id).then(setSelectedFDR);
          }
        }}
        currentRole={role}
      />

      <OCRReviewModal
        fdr={ocrTargetFDR}
        isOpen={isOCRModalOpen}
        onClose={() => {
          setIsOCRModalOpen(false);
          setOcrTargetFDR(null);
        }}
        onRefresh={() => {
          fetchFDRs();
          if (selectedFDR && ocrTargetFDR && selectedFDR.id === ocrTargetFDR.id) {
            fdrService.getById(selectedFDR.id).then(setSelectedFDR);
          }
        }}
      />

      <VerificationReportModal
        fdr={verificationTargetFDR}
        isOpen={isVerificationModalOpen}
        onClose={() => {
          setIsVerificationModalOpen(false);
          setVerificationTargetFDR(null);
        }}
        onRefresh={() => {
          fetchFDRs();
          if (selectedFDR && verificationTargetFDR && selectedFDR.id === verificationTargetFDR.id) {
            fdrService.getById(selectedFDR.id).then(setSelectedFDR);
          }
        }}
        currentRole={role}
      />

      <InitiateRenewalModal
        fdr={renewalTargetFDR}
        isOpen={isRenewalModalOpen}
        onClose={() => {
          setIsRenewalModalOpen(false);
          setRenewalTargetFDR(null);
        }}
        onSuccess={() => {
          fetchFDRs();
        }}
      />

      <RequestReleaseModal
        fdr={releaseTargetFDR}
        isOpen={isReleaseModalOpen}
        onClose={() => {
          setIsReleaseModalOpen(false);
          setReleaseTargetFDR(null);
        }}
        onSuccess={() => {
          fetchFDRs();
        }}
      />

      <AuthorityDecisionModal
        item={authorityTargetItem}
        type={authorityTargetType}
        isOpen={isAuthorityModalOpen}
        onClose={() => {
          setIsAuthorityModalOpen(false);
          setAuthorityTargetItem(null);
        }}
        onSuccess={() => {
          fetchFDRs();
          fetchApprovalQueue();
        }}
      />

    </div>
  );
}
