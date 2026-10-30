import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Building2, 
  Calendar, 
  Send 
} from 'lucide-react';
import { releaseService } from '../services/api';

export default function AuthorityDecisionModal({ item, type, isOpen, onClose, onSuccess }) {
  // type is 'FDR' or 'RELEASE'
  const [decision, setDecision] = useState(type === 'RELEASE' ? 'APPROVE_RELEASE' : 'APPROVE_FDR');
  const [remarks, setRemarks] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !item) return null;

  const isRelease = type === 'RELEASE';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!remarks.trim()) {
      setError("Please provide official remarks for your statutory decision.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (isRelease) {
        await releaseService.decideRelease(item.id, decision, remarks);
      } else {
        await releaseService.decideFDR(item.id, decision, remarks);
      }

      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error("Decision recording error:", err);
      setError(err.response?.data?.detail || "Failed to record statutory authority decision.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-800 to-teal-900 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5 text-emerald-300" />
            </div>
            <div>
              <h3 className="text-base font-bold">AICTE Competent Approving Authority Sign-Off</h3>
              <p className="text-xs text-emerald-100">
                {isRelease ? 'Statutory Authorization for Security Deposit Release' : 'Final Statutory Sign-Off on Scrutinized FDR'}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-white/70 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-700 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Dossier Information Card */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <span className="font-bold text-slate-700">Target Instrument:</span>
              <span className="font-mono font-bold text-primary">{isRelease ? item.fdr?.fdr_number || `#${item.fdr_id}` : item.fdr_number}</span>
            </div>

            {isRelease ? (
              <>
                <div className="flex justify-between text-slate-600">
                  <span>Release Reason:</span>
                  <span className="font-semibold text-slate-800">{item.release_reason}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Refund Bank &amp; Account:</span>
                  <span className="font-mono font-semibold">{item.refund_bank_name} ({item.refund_account_number})</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Refund IFSC:</span>
                  <span className="font-mono font-semibold">{item.refund_ifsc}</span>
                </div>
              </>
            ) : (
              <>
                <div className="flex justify-between text-slate-600">
                  <span>Bank &amp; Branch:</span>
                  <span className="font-semibold text-slate-800">{item.bank_name} ({item.branch_name})</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Deposit Amount:</span>
                  <span className="font-bold text-slate-800">₹ {Number(item.deposit_amount).toLocaleString('en-IN')}</span>
                </div>
                {item.scrutiny_remarks && (
                  <div className="bg-amber-50 p-2.5 rounded-lg border border-amber-200 text-amber-900 mt-2">
                    <span className="font-bold block text-[10px] uppercase">Scrutiny Officer Findings:</span>
                    <p className="mt-0.5">{item.scrutiny_remarks}</p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Decision Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700">Official Statutory Decision *</label>
            <div className="grid grid-cols-2 gap-3">
              <label className={`p-3.5 rounded-xl border cursor-pointer flex items-center space-x-2.5 transition ${
                decision.includes('APPROVE')
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-900 font-bold'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <input
                  type="radio"
                  name="decision"
                  value={isRelease ? 'APPROVE_RELEASE' : 'APPROVE_FDR'}
                  checked={decision.includes('APPROVE')}
                  onChange={(e) => setDecision(e.target.value)}
                  className="hidden"
                />
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                <div>
                  <div className="text-xs">{isRelease ? 'Authorize Release' : 'Approve & Activate'}</div>
                  <div className="text-[10px] text-slate-400 font-normal">Statutory approval</div>
                </div>
              </label>

              <label className={`p-3.5 rounded-xl border cursor-pointer flex items-center space-x-2.5 transition ${
                decision.includes('REJECT')
                  ? 'bg-rose-50 border-rose-400 text-rose-900 font-bold'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <input
                  type="radio"
                  name="decision"
                  value={isRelease ? 'REJECT_RELEASE' : 'REJECT_FDR'}
                  checked={decision.includes('REJECT')}
                  onChange={(e) => setDecision(e.target.value)}
                  className="hidden"
                />
                <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                <div>
                  <div className="text-xs">{isRelease ? 'Reject Release' : 'Statutory Rejection'}</div>
                  <div className="text-[10px] text-slate-400 font-normal">Withhold consent</div>
                </div>
              </label>
            </div>
          </div>

          {/* Remarks */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Authority Remarks &amp; Statutory Directives *</label>
            <textarea
              rows="3"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Record the official rationale, statutory conditions, or grounds for decision..."
              className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          {/* Action Footer */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
            <button
              type="button"
              onClick={onClose}
              className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-1.5 text-white ${
                decision.includes('APPROVE') ? 'bg-emerald-700 hover:bg-emerald-800' : 'bg-rose-700 hover:bg-rose-800'
              } disabled:opacity-50`}
            >
              <Send className="w-3.5 h-3.5" />
              <span>{loading ? 'Recording Decision...' : 'Record Statutory Decision'}</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
