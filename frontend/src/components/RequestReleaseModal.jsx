import React, { useState, useEffect } from 'react';
import { 
  X, 
  DollarSign, 
  AlertTriangle, 
  CheckCircle2, 
  Building2, 
  FileText, 
  Send,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import { releaseService } from '../services/api';

export default function RequestReleaseModal({ fdr, isOpen, onClose, onSuccess }) {
  const [reason, setReason] = useState('');
  const [bankName, setBankName] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [ifsc, setIfsc] = useState('');
  const [beneficiaryName, setBeneficiaryName] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && fdr) {
      setReason('Statutory fixed deposit tenure completed as per AICTE Approval Process Handbook (APH) guidelines.');
      setBankName(fdr.bank_name || '');
      setAccountNumber('');
      setIfsc(fdr.ifsc_code || '');
      setBeneficiaryName(fdr.joint_holder || 'Institution Operating Account');
      setError(null);
    }
  }, [isOpen, fdr]);

  if (!isOpen || !fdr) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const payload = {
        release_reason: reason,
        refund_bank_name: bankName,
        refund_account_number: accountNumber,
        refund_ifsc: ifsc,
        refund_beneficiary_name: beneficiaryName
      };

      const res = await releaseService.requestRelease(fdr.id, payload);
      if (onSuccess) onSuccess(res);
      onClose();
    } catch (err) {
      console.error("Release request failed:", err);
      setError(err.response?.data?.detail || "Failed to submit release petition. Ensure all compliance conditions are met.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-emerald-600 text-white rounded-xl flex items-center justify-center font-bold">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">Petition for Security Deposit Release / Refund</h3>
              <p className="text-xs text-slate-500">
                FDR <span className="font-mono font-bold text-primary">{fdr.fdr_number}</span> (Principal: ₹ {Number(fdr.deposit_amount).toLocaleString('en-IN')})
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-700 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Statutory Conditions Checklist */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs space-y-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wide block">Statutory Eligibility Pre-Conditions</span>
            <div className="flex items-center space-x-2 text-slate-700">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>FDR is in active or matured custody ({fdr.lifecycle_status}).</span>
            </div>
            <div className="flex items-center space-x-2 text-slate-700">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Zero open compliance discrepancies recorded on the verification dossier.</span>
            </div>
          </div>

          {/* Release Reason */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Reason &amp; Legal Justification for Release *</label>
            <textarea
              rows="3"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="State the regulatory grounds for releasing this security deposit (e.g. completion of 10-year term, closure of academic program)..."
              className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          {/* Refund Bank Details */}
          <div className="pt-2 border-t border-slate-100 space-y-3">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
              Bank Account for Refund / Principal Credit
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-700">Beneficiary Bank Name *</label>
                <input
                  type="text"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-lg"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-700">Branch IFSC Code *</label>
                <input
                  type="text"
                  value={ifsc}
                  onChange={(e) => setIfsc(e.target.value.toUpperCase())}
                  className="w-full text-xs font-mono px-3 py-1.5 border border-slate-300 rounded-lg"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-700">Account Number *</label>
                <input
                  type="text"
                  value={accountNumber}
                  onChange={(e) => setAccountNumber(e.target.value)}
                  placeholder="e.g. 10023456789"
                  className="w-full text-xs font-mono px-3 py-1.5 border border-slate-300 rounded-lg"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-700">Account Holder Name *</label>
                <input
                  type="text"
                  value={beneficiaryName}
                  onChange={(e) => setBeneficiaryName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-lg"
                  required
                />
              </div>
            </div>
          </div>

          {/* Footer Actions */}
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
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{loading ? 'Submitting Petition...' : 'Submit Release Petition'}</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
