import React, { useState, useEffect } from 'react';
import { 
  X, 
  RefreshCw, 
  FileText, 
  Calendar, 
  Building2, 
  AlertTriangle, 
  CheckCircle2, 
  Upload, 
  ArrowRight,
  ShieldCheck 
} from 'lucide-react';
import { lifecycleService, fdrService } from '../services/api';

export default function InitiateRenewalModal({ fdr, isOpen, onClose, onSuccess }) {
  const [fdrNumber, setFdrNumber] = useState('');
  const [bankName, setBankName] = useState('');
  const [branchName, setBranchName] = useState('');
  const [ifscCode, setIfscCode] = useState('');
  const [depositAmount, setDepositAmount] = useState('');
  const [issueDate, setIssueDate] = useState('');
  const [maturityDate, setMaturityDate] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [beneficiary, setBeneficiary] = useState('');
  const [file, setFile] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && fdr) {
      const today = new Date().toISOString().split('T')[0];
      const nextThreeYears = new Date();
      nextThreeYears.setFullYear(nextThreeYears.getFullYear() + 3);
      const matStr = nextThreeYears.toISOString().split('T')[0];

      setFdrNumber(`${fdr.fdr_number}-R1`);
      setBankName(fdr.bank_name || '');
      setBranchName(fdr.branch_name || '');
      setIfscCode(fdr.ifsc_code || '');
      setDepositAmount(fdr.deposit_amount || '');
      setIssueDate(today);
      setMaturityDate(matStr);
      setInterestRate(fdr.interest_rate || '7.10');
      setBeneficiary(fdr.beneficiary || 'Member Secretary, AICTE New Delhi');
      setFile(null);
      setError(null);
    }
  }, [isOpen, fdr]);

  if (!isOpen || !fdr) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // 1. Create renewal instrument linked to previous_fdr_id
      const payload = {
        fdr_number: fdrNumber,
        bank_name: bankName,
        branch_name: branchName,
        ifsc_code: ifscCode,
        deposit_amount: depositAmount,
        issue_date: issueDate,
        maturity_date: maturityDate,
        interest_rate: interestRate ? interestRate : null,
        beneficiary: beneficiary,
        joint_holder: fdr.joint_holder || null,
        instrument_type: fdr.instrument_type || "Fixed Deposit Receipt",
        is_auto_renewal: false
      };

      const renewedFdr = await lifecycleService.initiateRenewal(fdr.id, payload);

      // 2. If certificate file selected, upload immediately
      if (file && renewedFdr && renewedFdr.id) {
        try {
          await fdrService.uploadDocument(renewedFdr.id, file, "PRIMARY_INSTRUMENT");
        } catch (uploadErr) {
          console.warn("Document upload warning:", uploadErr);
        }
      }

      if (onSuccess) onSuccess(renewedFdr);
      onClose();
    } catch (err) {
      console.error("Renewal failed:", err);
      setError(err.response?.data?.detail || "Failed to initiate renewal. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-amber-600 text-white rounded-xl flex items-center justify-center font-bold">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">Initiate FDR Statutory Renewal</h3>
              <p className="text-xs text-slate-500">
                Extending statutory deposit security for FDR <span className="font-mono font-bold text-primary">{fdr.fdr_number}</span>
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

          {/* Lineage Info Banner */}
          <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-3 flex items-center justify-between text-xs text-blue-900">
            <div className="flex items-center space-x-2">
              <span className="font-semibold">Original Instrument:</span>
              <span className="font-mono font-bold text-primary">{fdr.fdr_number}</span>
              <span>(Matured: {fdr.maturity_date})</span>
            </div>
            <div className="flex items-center space-x-1 font-bold text-amber-700">
              <ArrowRight className="w-3.5 h-3.5" />
              <span>Chaining Lineage</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* New FDR Number */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">New / Renewed Certificate Number *</label>
              <input
                type="text"
                value={fdrNumber}
                onChange={(e) => setFdrNumber(e.target.value)}
                placeholder="e.g. FDR-SBI-2027-RNW"
                className="w-full text-xs font-mono px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>

            {/* Deposit Amount */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Renewed Deposit Principal (₹) *</label>
              <input
                type="number"
                step="0.01"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                className="w-full text-xs font-semibold px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>

            {/* Bank Name */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Issuing Bank *</label>
              <input
                type="text"
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg bg-slate-50"
                required
              />
            </div>

            {/* Branch Name */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Branch Name *</label>
              <input
                type="text"
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>

            {/* IFSC Code */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">IFSC Code *</label>
              <input
                type="text"
                value={ifscCode}
                onChange={(e) => setIfscCode(e.target.value.toUpperCase())}
                className="w-full text-xs font-mono px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>

            {/* Interest Rate */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Contracted Interest Rate (% p.a.)</label>
              <input
                type="number"
                step="0.01"
                value={interestRate}
                onChange={(e) => setInterestRate(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>

            {/* Issue Date */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Renewal Issue Date *</label>
              <input
                type="date"
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>

            {/* Maturity Date */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">New Extended Maturity Date *</label>
              <input
                type="date"
                value={maturityDate}
                onChange={(e) => setMaturityDate(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>

          </div>

          {/* Beneficiary */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Beneficiary Authority</label>
            <input
              type="text"
              value={beneficiary}
              onChange={(e) => setBeneficiary(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-700"
              required
            />
          </div>

          {/* Upload Renewed Certificate */}
          <div className="space-y-1 pt-2">
            <label className="text-xs font-bold text-slate-700">Attach Scanned Renewal Deposit Certificate (PDF / Image)</label>
            <div className="border border-dashed border-slate-300 rounded-lg p-3 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs text-slate-600">
                <Upload className="w-4 h-4 text-slate-400" />
                <span>{file ? file.name : 'Choose signed renewal certificate copy...'}</span>
              </div>
              <label className="cursor-pointer bg-white hover:bg-slate-100 text-slate-700 font-semibold text-xs px-3 py-1 rounded-md border border-slate-300 transition">
                Browse
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setFile(e.target.files[0])}
                  className="hidden"
                />
              </label>
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
              className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Submitting Renewal...' : 'Submit Statutory Renewal'}</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}

