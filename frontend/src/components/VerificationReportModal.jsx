import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  FileText,
  Clock,
  Send,
  MessageSquare,
  Check,
  Slash,
  ChevronDown,
  ChevronUp,
  Sliders,
  Sparkles,
  Info
} from 'lucide-react';
import { verificationService } from '../services/api';

export default function VerificationReportModal({ fdr, isOpen, onClose, onRefresh, currentRole }) {
  const [loading, setLoading] = useState(false);
  const [runningVerify, setRunningVerify] = useState(false);
  const [report, setReport] = useState(null);
  const [discrepancies, setDiscrepancies] = useState([]);
  const [activeTab, setActiveTab] = useState('rules'); // 'rules', 'discrepancies', 'recommendation'
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Institution response input state (mapped by discrepancy ID)
  const [responseTextMap, setResponseTextMap] = useState({});
  const [submittingResponseId, setSubmittingResponseId] = useState(null);

  // Scrutiny resolution input state
  const [resolutionNoteMap, setResolutionNoteMap] = useState({});
  const [resolvingId, setResolvingId] = useState(null);

  // Manual observation state
  const [showAddObservation, setShowAddObservation] = useState(false);
  const [obsTitle, setObsTitle] = useState('');
  const [obsDesc, setObsDesc] = useState('');
  const [obsSeverity, setObsSeverity] = useState('HIGH');
  const [raisingObs, setRaisingObs] = useState(false);

  // Scrutiny recommendation state
  const [recommendation, setRecommendation] = useState('RECOMMEND_APPROVAL');
  const [recommendationRemarks, setRecommendationRemarks] = useState('');
  const [submittingRec, setSubmittingRec] = useState(false);

  useEffect(() => {
    if (isOpen && fdr) {
      loadData();
    }
  }, [isOpen, fdr]);

  const loadData = async () => {
    setLoading(true);
    setActionError(null);
    try {
      const [reportData, discData] = await Promise.all([
        verificationService.getReport(fdr.id).catch(() => null),
        verificationService.getDiscrepancies(fdr.id).catch(() => [])
      ]);
      setReport(reportData);
      setDiscrepancies(discData || []);
    } catch (err) {
      console.error("Failed to load verification dossier:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunVerification = async () => {
    setRunningVerify(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const newReport = await verificationService.verify(fdr.id);
      setReport(newReport);
      const updatedDiscs = await verificationService.getDiscrepancies(fdr.id);
      setDiscrepancies(updatedDiscs || []);
      setActionSuccess("12-rule verification engine evaluated successfully.");
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Verification execution error:", err);
      setActionError(err.response?.data?.detail || "Failed to execute verification engine.");
    } finally {
      setRunningVerify(false);
    }
  };

  const handleRespondToDiscrepancy = async (discId) => {
    const text = responseTextMap[discId];
    if (!text || text.trim().length === 0) return;

    setSubmittingResponseId(discId);
    setActionError(null);
    try {
      await verificationService.respondToDiscrepancy(discId, text);
      setActionSuccess("Institution response recorded.");
      setResponseTextMap(prev => ({ ...prev, [discId]: '' }));
      const updatedDiscs = await verificationService.getDiscrepancies(fdr.id);
      setDiscrepancies(updatedDiscs);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.response?.data?.detail || "Failed to submit response.");
    } finally {
      setSubmittingResponseId(null);
    }
  };

  const handleResolveDiscrepancy = async (discId, status = 'RESOLVED') => {
    const note = resolutionNoteMap[discId] || (status === 'RESOLVED' ? "Verified and resolved by Scrutiny Officer." : "Waived by Scrutiny Authority.");
    setResolvingId(discId);
    setActionError(null);
    try {
      await verificationService.resolveDiscrepancy(discId, note, status);
      setActionSuccess(`Discrepancy marked as ${status}.`);
      setResolutionNoteMap(prev => ({ ...prev, [discId]: '' }));
      const updatedDiscs = await verificationService.getDiscrepancies(fdr.id);
      setDiscrepancies(updatedDiscs);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.response?.data?.detail || "Failed to resolve discrepancy.");
    } finally {
      setResolvingId(null);
    }
  };

  const handleRaiseObservation = async (e) => {
    e.preventDefault();
    if (!obsTitle.trim() || !obsDesc.trim()) return;

    setRaisingObs(true);
    setActionError(null);
    try {
      await verificationService.raiseDiscrepancy(fdr.id, {
        title: obsTitle,
        description: obsDesc,
        severity: obsSeverity,
        rule_code: 'SCRUTINY_OFFICER_OBSERVATION'
      });
      setObsTitle('');
      setObsDesc('');
      setShowAddObservation(false);
      setActionSuccess("Observation raised and flagged on FDR dossier.");
      const updatedDiscs = await verificationService.getDiscrepancies(fdr.id);
      setDiscrepancies(updatedDiscs);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.response?.data?.detail || "Failed to raise observation.");
    } finally {
      setRaisingObs(false);
    }
  };

  const handleSubmitRecommendation = async (e) => {
    e.preventDefault();
    if (!recommendationRemarks.trim()) return;

    setSubmittingRec(true);
    setActionError(null);
    try {
      await verificationService.submitScrutinyRecommendation(fdr.id, recommendation, recommendationRemarks);
      setActionSuccess(`Scrutiny recommendation '${recommendation}' successfully recorded.`);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.response?.data?.detail || "Failed to submit scrutiny recommendation.");
    } finally {
      setSubmittingRec(false);
    }
  };

  if (!isOpen || !fdr) return null;

  const isOfficer = currentRole === 'ROLE_SCRUTINY_OFFICER' || currentRole === 'ROLE_SYSTEM_ADMIN';
  const isInstitution = currentRole === 'ROLE_INSTITUTION_ADMIN';

  const getVerdictBadge = (status) => {
    switch (status) {
      case 'PASSED':
        return (
          <div className="bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm">Regulatory Compliance Verified (PASSED)</h4>
                <p className="text-xs text-emerald-700">All 12 statutory, IFSC, tenure, amount, and duplicate rules fully satisfied.</p>
              </div>
            </div>
            <span className="bg-emerald-600 text-white font-bold text-xs px-3 py-1 rounded-full uppercase">Clean Pass</span>
          </div>
        );
      case 'PASSED_WITH_WARNINGS':
        return (
          <div className="bg-amber-50 border border-amber-300 text-amber-900 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm">Compliant With Observations (WARNINGS)</h4>
                <p className="text-xs text-amber-800">Passed mandatory requirements, but minor heuristic anomalies or remarks flagged.</p>
              </div>
            </div>
            <span className="bg-amber-500 text-white font-bold text-xs px-3 py-1 rounded-full uppercase">Observations</span>
          </div>
        );
      case 'FAILED_DISCREPANCIES':
        return (
          <div className="bg-rose-50 border border-rose-300 text-rose-900 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <XCircle className="w-6 h-6 text-rose-600 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm">Discrepancies Detected (FAILED)</h4>
                <p className="text-xs text-rose-800">One or more CRITICAL/HIGH severity verification checks failed. Action required before approval.</p>
              </div>
            </div>
            <span className="bg-rose-600 text-white font-bold text-xs px-3 py-1 rounded-full uppercase">Discrepancy</span>
          </div>
        );
      default:
        return (
          <div className="bg-slate-50 border border-slate-300 text-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Info className="w-6 h-6 text-slate-500 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm">Verification Engine Not Evaluated</h4>
                <p className="text-xs text-slate-600">Click "Run Verification Engine" below to execute all 12 checks.</p>
              </div>
            </div>
            <button
              onClick={handleRunVerification}
              disabled={runningVerify}
              className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-3 py-1.5 rounded-lg transition"
            >
              {runningVerify ? 'Evaluating...' : 'Evaluate Now'}
            </button>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-amber-600 text-white rounded-xl flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-800">Intelligent Verification &amp; Scrutiny Dossier</h3>
                <span className="bg-slate-100 font-mono text-primary font-bold px-2 py-0.5 rounded text-xs">
                  {fdr.fdr_number}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {fdr.bank_name} • Deposit: ₹ {Number(fdr.deposit_amount).toLocaleString('en-IN')} • Tenure: {fdr.issue_date} to {fdr.maturity_date}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              id="re-verify-btn"
              onClick={handleRunVerification}
              disabled={runningVerify}
              className="bg-secondary hover:bg-secondary-hover text-primary font-semibold text-xs px-3.5 py-2 rounded-lg border border-blue-200 transition flex items-center space-x-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningVerify ? 'animate-spin' : ''}`} />
              <span>{runningVerify ? 'Evaluating...' : 'Re-run 12 Rules'}</span>
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Status Alerts */}
        {actionError && (
          <div className="bg-rose-50 border-b border-rose-200 px-6 py-2.5 text-xs text-rose-700 font-medium flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{actionError}</span>
          </div>
        )}
        {actionSuccess && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-2.5 text-xs text-emerald-800 font-medium flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 flex items-center space-x-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('rules')}
            className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'rules'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Rule Evaluation Breakdown ({report?.rule_results?.length || 12})</span>
          </button>

          <button
            onClick={() => setActiveTab('discrepancies')}
            className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'discrepancies'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Discrepancy Tracker ({discrepancies.length})</span>
          </button>

          {isOfficer && (
            <button
              onClick={() => setActiveTab('recommendation')}
              className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
                activeTab === 'recommendation'
                  ? 'border-primary text-primary font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Send className="w-4 h-4" />
              <span>Officer Scrutiny Recommendation</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Verdict Banner */}
          {getVerdictBadge(report?.overall_status)}

          {/* TAB 1: 12-RULE BREAKDOWN */}
          {activeTab === 'rules' && (
            <div className="space-y-4">
              {/* Scorecard Mini Stats */}
              {report && (
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Total Evaluated</span>
                    <h5 className="text-xl font-bold text-slate-800">{report.total_rules_evaluated}</h5>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-lg text-center">
                    <span className="text-[10px] uppercase font-bold text-emerald-600">Passed</span>
                    <h5 className="text-xl font-bold text-emerald-700">{report.passed_count}</h5>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-center">
                    <span className="text-[10px] uppercase font-bold text-amber-600">Warnings</span>
                    <h5 className="text-xl font-bold text-amber-700">{report.warning_count}</h5>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 p-3 rounded-lg text-center">
                    <span className="text-[10px] uppercase font-bold text-rose-600">Failed</span>
                    <h5 className="text-xl font-bold text-rose-700">{report.failed_count}</h5>
                  </div>
                </div>
              )}

              {/* Rules Cards List */}
              <div className="space-y-2.5">
                {report && report.rule_results && report.rule_results.length > 0 ? (
                  report.rule_results.map((rule, idx) => (
                    <div
                      key={rule.rule_code || idx}
                      className={`p-4 rounded-xl border transition ${
                        rule.status === 'PASSED'
                          ? 'bg-white border-slate-200 hover:border-emerald-300'
                          : rule.status === 'WARNING'
                          ? 'bg-amber-50/40 border-amber-200'
                          : rule.status === 'FAILED'
                          ? 'bg-rose-50/40 border-rose-200'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3">
                          <div className="mt-0.5">
                            {rule.status === 'PASSED' && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                            {rule.status === 'WARNING' && <AlertTriangle className="w-5 h-5 text-amber-600" />}
                            {rule.status === 'FAILED' && <XCircle className="w-5 h-5 text-rose-600" />}
                            {rule.status === 'SKIPPED' && <Slash className="w-5 h-5 text-slate-400" />}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h5 className="text-xs font-bold text-slate-800">{rule.name}</h5>
                              <span className="text-[10px] font-mono text-slate-400">({rule.rule_code})</span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                                rule.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-700' :
                                rule.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                                'bg-blue-100 text-primary'
                              }`}>
                                {rule.severity}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 mt-1">{rule.message}</p>
                            
                            {(rule.expected || rule.actual) && (
                              <div className="mt-2 text-[11px] grid grid-cols-2 gap-2 bg-slate-50 p-2 rounded-md border border-slate-100 font-mono">
                                <div>
                                  <span className="text-slate-400 block text-[9px] uppercase font-sans">Expected</span>
                                  <span className="text-slate-700">{rule.expected || '-'}</span>
                                </div>
                                <div>
                                  <span className="text-slate-400 block text-[9px] uppercase font-sans">Actual Received</span>
                                  <span className={rule.status === 'FAILED' ? 'text-rose-700 font-bold' : 'text-slate-700'}>
                                    {rule.actual || '-'}
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          rule.status === 'PASSED' ? 'bg-emerald-100 text-emerald-800' :
                          rule.status === 'WARNING' ? 'bg-amber-100 text-amber-800' :
                          rule.status === 'FAILED' ? 'bg-rose-100 text-rose-800' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {rule.status}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-xs text-slate-400">
                    No evaluation data loaded. Click "Re-run 12 Rules" to evaluate this instrument.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: DISCREPANCY TRACKER */}
          {activeTab === 'discrepancies' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div>
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                    Identified Discrepancies &amp; Scrutiny Observations ({discrepancies.length})
                  </h4>
                  <p className="text-xs text-slate-500">Track and respond to compliance observations</p>
                </div>

                {isOfficer && (
                  <button
                    onClick={() => setShowAddObservation(!showAddObservation)}
                    className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-3 py-1.5 rounded-lg transition"
                  >
                    {showAddObservation ? 'Cancel' : '+ Raise Custom Observation'}
                  </button>
                )}
              </div>

              {/* Add Custom Observation Form (Officer Only) */}
              {showAddObservation && isOfficer && (
                <form onSubmit={handleRaiseObservation} className="bg-amber-50/50 p-4 rounded-xl border border-amber-200 space-y-3">
                  <h5 className="text-xs font-bold text-amber-900">Raise Scrutiny Officer Observation</h5>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="md:col-span-2 space-y-1">
                      <label className="text-[11px] font-bold text-slate-700">Observation Title</label>
                      <input
                        type="text"
                        value={obsTitle}
                        onChange={(e) => setObsTitle(e.target.value)}
                        placeholder="e.g. Bank seal illegible or joint holder missing"
                        className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-lg bg-white"
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] font-bold text-slate-700">Severity</label>
                      <select
                        value={obsSeverity}
                        onChange={(e) => setObsSeverity(e.target.value)}
                        className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-lg bg-white"
                      >
                        <option value="CRITICAL">CRITICAL (Blocks Approval)</option>
                        <option value="HIGH">HIGH (Requires Resolution)</option>
                        <option value="MEDIUM">MEDIUM (Observation)</option>
                        <option value="LOW">LOW (Informational)</option>
                      </select>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-slate-700">Detailed Description &amp; Required Remediation</label>
                    <textarea
                      rows="2"
                      value={obsDesc}
                      onChange={(e) => setObsDesc(e.target.value)}
                      placeholder="Specify the issue observed during manual examination and instructions for the institution."
                      className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white"
                      required
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="submit"
                      disabled={raisingObs}
                      className="bg-amber-700 hover:bg-amber-800 text-white font-semibold text-xs px-4 py-1.5 rounded-lg transition"
                    >
                      {raisingObs ? 'Recording...' : 'Record Observation'}
                    </button>
                  </div>
                </form>
              )}

              {/* Discrepancies List */}
              <div className="space-y-3">
                {discrepancies.length > 0 ? (
                  discrepancies.map((disc) => (
                    <div key={disc.id} className="p-4 rounded-xl border border-slate-200 bg-white space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                              disc.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-700' :
                              disc.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                              'bg-amber-100 text-amber-700'
                            }`}>
                              {disc.severity}
                            </span>
                            <h5 className="text-xs font-bold text-slate-800">{disc.title}</h5>
                            <span className="text-[10px] text-slate-400 font-mono">#{disc.id}</span>
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{disc.description}</p>
                        </div>

                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                          disc.status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-800' :
                          disc.status === 'WAIVED' ? 'bg-blue-100 text-primary' :
                          'bg-rose-100 text-rose-800'
                        }`}>
                          {disc.status}
                        </span>
                      </div>

                      {/* Institution Response View / Form */}
                      {disc.institution_response ? (
                        <div className="bg-blue-50/50 border border-blue-200 rounded-lg p-3 text-xs space-y-1">
                          <span className="text-[10px] font-bold text-primary uppercase">Institution Official Response:</span>
                          <p className="text-slate-700">{disc.institution_response}</p>
                          {disc.responded_at && (
                            <span className="text-[10px] text-slate-400 font-mono block">
                              Submitted: {new Date(disc.responded_at).toLocaleString()}
                            </span>
                          )}
                        </div>
                      ) : isInstitution && disc.status === 'OPEN' ? (
                        <div className="space-y-1.5 pt-2 border-t border-slate-100">
                          <label className="text-[11px] font-bold text-slate-700">Submit Institutional Clarification / Response</label>
                          <div className="flex items-center space-x-2">
                            <input
                              type="text"
                              value={responseTextMap[disc.id] || ''}
                              onChange={(e) => setResponseTextMap({ ...responseTextMap, [disc.id]: e.target.value })}
                              placeholder="Type explanation or document reference to address this observation..."
                              className="flex-1 text-xs px-3 py-1.5 border border-slate-300 rounded-lg"
                            />
                            <button
                              onClick={() => handleRespondToDiscrepancy(disc.id)}
                              disabled={submittingResponseId === disc.id}
                              className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition"
                            >
                              {submittingResponseId === disc.id ? 'Sending...' : 'Respond'}
                            </button>
                          </div>
                        </div>
                      ) : null}

                      {/* Officer Resolution Notes & Actions */}
                      {disc.officer_resolution_note ? (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 text-xs">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase">Officer Resolution Note:</span>
                          <p className="text-slate-700">{disc.officer_resolution_note}</p>
                        </div>
                      ) : isOfficer && disc.status === 'OPEN' ? (
                        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
                          <input
                            type="text"
                            placeholder="Resolution or waiver note..."
                            value={resolutionNoteMap[disc.id] || ''}
                            onChange={(e) => setResolutionNoteMap({ ...resolutionNoteMap, [disc.id]: e.target.value })}
                            className="text-xs px-2.5 py-1 border border-slate-200 rounded-md w-64"
                          />
                          <button
                            onClick={() => handleResolveDiscrepancy(disc.id, 'RESOLVED')}
                            disabled={resolvingId === disc.id}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] px-3 py-1 rounded-md transition"
                          >
                            Mark Resolved
                          </button>
                          <button
                            onClick={() => handleResolveDiscrepancy(disc.id, 'WAIVED')}
                            disabled={resolvingId === disc.id}
                            className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold text-[11px] px-3 py-1 rounded-md transition"
                          >
                            Waive
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                    No open discrepancies recorded. The instrument passed all evaluated regulatory rules.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: SCRUTINY OFFICER RECOMMENDATION */}
          {activeTab === 'recommendation' && isOfficer && (
            <form onSubmit={handleSubmitRecommendation} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-800">Record AICTE Scrutiny Officer Recommendation</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Your recommendation and findings will be forwarded to the AICTE Competent Approving Authority for final statutory sign-off.
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-700">Official Recommendation</label>
                <div className="grid grid-cols-3 gap-3">
                  <label className={`p-3 rounded-lg border cursor-pointer text-center transition ${
                    recommendation === 'RECOMMEND_APPROVAL' ? 'bg-emerald-50 border-emerald-400 text-emerald-800 font-bold' : 'bg-white border-slate-200 text-slate-600'
                  }`}>
                    <input
                      type="radio"
                      name="recommendation"
                      value="RECOMMEND_APPROVAL"
                      checked={recommendation === 'RECOMMEND_APPROVAL'}
                      onChange={() => setRecommendation('RECOMMEND_APPROVAL')}
                      className="hidden"
                    />
                    <div className="text-xs">Recommend Approval</div>
                    <div className="text-[10px] text-slate-400 font-normal mt-0.5">All checks verified</div>
                  </label>

                  <label className={`p-3 rounded-lg border cursor-pointer text-center transition ${
                    recommendation === 'NEED_MORE_DOCUMENTS' ? 'bg-amber-50 border-amber-400 text-amber-800 font-bold' : 'bg-white border-slate-200 text-slate-600'
                  }`}>
                    <input
                      type="radio"
                      name="recommendation"
                      value="NEED_MORE_DOCUMENTS"
                      checked={recommendation === 'NEED_MORE_DOCUMENTS'}
                      onChange={() => setRecommendation('NEED_MORE_DOCUMENTS')}
                      className="hidden"
                    />
                    <div className="text-xs">Request Documents</div>
                    <div className="text-[10px] text-slate-400 font-normal mt-0.5">Return to institution</div>
                  </label>

                  <label className={`p-3 rounded-lg border cursor-pointer text-center transition ${
                    recommendation === 'RECOMMEND_REJECTION' ? 'bg-rose-50 border-rose-400 text-rose-800 font-bold' : 'bg-white border-slate-200 text-slate-600'
                  }`}>
                    <input
                      type="radio"
                      name="recommendation"
                      value="RECOMMEND_REJECTION"
                      checked={recommendation === 'RECOMMEND_REJECTION'}
                      onChange={() => setRecommendation('RECOMMEND_REJECTION')}
                      className="hidden"
                    />
                    <div className="text-xs">Recommend Rejection</div>
                    <div className="text-[10px] text-slate-400 font-normal mt-0.5">Critical defects</div>
                  </label>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Detailed Scrutiny Remarks &amp; Statutory Justification</label>
                <textarea
                  rows="4"
                  value={recommendationRemarks}
                  onChange={(e) => setRecommendationRemarks(e.target.value)}
                  placeholder="Record comprehensive scrutiny findings, bank verification notes, and exact reasons for recommendation..."
                  className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submittingRec}
                  className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submittingRec ? 'Submitting...' : 'Submit Scrutiny Recommendation'}</span>
                </button>
              </div>
            </form>
          )}

        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex items-center justify-between">
          <div className="text-[11px] text-slate-500">
            FDRSetu Intelligent Verification Engine v1.0 • AICTE Smart Automation
          </div>
          <button
            onClick={onClose}
            className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-1.5 rounded-lg hover:bg-slate-200 transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
