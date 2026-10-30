import React, { useState } from 'react';
import { 
  X, 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Building2, 
  Calendar, 
  DollarSign, 
  ShieldCheck, 
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { fdrService } from '../services/api';

const POPULAR_BANKS = [
  "State Bank of India",
  "Punjab National Bank",
  "Bank of Baroda",
  "Canara Bank",
  "Union Bank of India",
  "HDFC Bank",
  "ICICI Bank",
  "Axis Bank",
  "Kotak Mahindra Bank",
  "Indian Bank"
];

export default function NewFDRModal({ isOpen, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    fdr_number: '',
    bank_name: 'State Bank of India',
    branch_name: '',
    ifsc_code: '',
    deposit_amount: '',
    issue_date: '',
    maturity_date: '',
    interest_rate: '7.10',
    beneficiary: 'Member Secretary, AICTE / Regional Officer, AICTE',
    joint_holder: '',
    instrument_type: 'Fixed Deposit Receipt',
    is_auto_renewal: false
  });

  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [autoSubmitScrutiny, setAutoSubmitScrutiny] = useState(true);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleFileChange = (e) => {
    setFileError(null);
    const file = e.target.files[0];
    if (!file) return;

    // File size check (10MB)
    if (file.size > 10 * 1024 * 1024) {
      setFileError("File exceeds maximum allowed size of 10MB");
      return;
    }

    const allowed = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    if (!allowed.includes(file.type)) {
      setFileError("Only PDF, JPG, and PNG files are accepted");
      return;
    }

    setSelectedFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Date validation
    if (new Date(formData.maturity_date) <= new Date(formData.issue_date)) {
      setError("Maturity date must be after the issue date");
      return;
    }

    // IFSC validation
    const ifscRegex = /^[A-Z]{4}0[A-Z0-9]{6}$/;
    if (!ifscRegex.test(formData.ifsc_code.trim().toUpperCase())) {
      setError("Invalid IFSC format. Must be 11 characters (e.g. SBIN0001234, 5th character must be '0')");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        ifsc_code: formData.ifsc_code.trim().toUpperCase(),
        deposit_amount: parseFloat(formData.deposit_amount),
        interest_rate: formData.interest_rate ? parseFloat(formData.interest_rate) : null
      };

      // 1. Create FDR
      const createdFDR = await fdrService.create(payload);

      // 2. Upload Document if selected
      if (selectedFile) {
        await fdrService.uploadDocument(createdFDR.id, selectedFile, "FDR_INSTRUMENT");

        // 3. Auto-submit for scrutiny if requested
        if (autoSubmitScrutiny) {
          await fdrService.submitForScrutiny(createdFDR.id);
        }
      }

      onSuccess(createdFDR);
      onClose();
    } catch (err) {
      console.error("FDR submission error:", err);
      setError(
        err.response?.data?.detail || "Failed to submit FDR record. Please verify fields."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="bg-primary text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold">Submit New Security Deposit (FDR)</h3>
              <p className="text-xs text-blue-100">AICTE Regulatory Compliance &amp; Verification Submission</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-blue-100 hover:text-white p-1 rounded-lg hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Container */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {error && (
            <div className="p-3.5 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2.5 text-xs text-danger">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Section 1: Financial Instrument Particulars */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 pb-1 border-b border-slate-100 flex items-center space-x-1.5">
              <Building2 className="w-4 h-4 text-primary" />
              <span>Bank &amp; Instrument Identifiers</span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Issuing Bank *
                </label>
                <select
                  name="bank_name"
                  value={formData.bank_name}
                  onChange={handleChange}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white text-slate-800"
                >
                  {POPULAR_BANKS.map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Branch Name *
                </label>
                <input
                  type="text"
                  name="branch_name"
                  value={formData.branch_name}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Vasant Kunj Branch"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Bank IFSC Code *
                </label>
                <input
                  type="text"
                  name="ifsc_code"
                  value={formData.ifsc_code}
                  onChange={handleChange}
                  required
                  maxLength={11}
                  placeholder="e.g. SBIN0001234"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary font-mono uppercase text-slate-800"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  FDR / Receipt Certificate Number *
                </label>
                <input
                  type="text"
                  name="fdr_number"
                  value={formData.fdr_number}
                  onChange={handleChange}
                  required
                  placeholder="e.g. FDR-SBI-2026-887766"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary font-mono font-semibold text-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Principal Amount (₹) *
                </label>
                <input
                  type="number"
                  name="deposit_amount"
                  value={formData.deposit_amount}
                  onChange={handleChange}
                  required
                  min="1000"
                  step="100"
                  placeholder="e.g. 3500000"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary font-semibold text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Dates and Terms */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 pb-1 border-b border-slate-100 flex items-center space-x-1.5">
              <Calendar className="w-4 h-4 text-primary" />
              <span>Tenure, Validity &amp; Ownership</span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Date of Issuance *
                </label>
                <input
                  type="date"
                  name="issue_date"
                  value={formData.issue_date}
                  onChange={handleChange}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Date of Maturity *
                </label>
                <input
                  type="date"
                  name="maturity_date"
                  value={formData.maturity_date}
                  onChange={handleChange}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Interest Rate (% p.a.)
                </label>
                <input
                  type="number"
                  name="interest_rate"
                  value={formData.interest_rate}
                  onChange={handleChange}
                  step="0.05"
                  placeholder="e.g. 7.10"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-800"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Beneficiary (AICTE Statutory Authority) *
                </label>
                <input
                  type="text"
                  name="beneficiary"
                  value={formData.beneficiary}
                  onChange={handleChange}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-slate-50 text-slate-700"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Joint / Institution Holder
                </label>
                <input
                  type="text"
                  name="joint_holder"
                  value={formData.joint_holder}
                  onChange={handleChange}
                  placeholder="e.g. Institution Name"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Document Upload */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 pb-1 border-b border-slate-100 flex items-center space-x-1.5">
              <Upload className="w-4 h-4 text-primary" />
              <span>Digital Instrument Copy (PDF / Image) *</span>
            </h4>

            <div className="border-2 border-dashed border-slate-300 hover:border-primary rounded-xl p-6 text-center bg-slate-50 hover:bg-blue-50/20 transition cursor-pointer relative">
              <input
                id="fdr-file-input"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="space-y-2">
                <div className="w-10 h-10 bg-blue-100 text-primary rounded-full flex items-center justify-center mx-auto">
                  <Upload className="w-5 h-5" />
                </div>
                {selectedFile ? (
                  <div className="text-xs font-semibold text-slate-800 flex items-center justify-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-success" />
                    <span>Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ) : (
                  <>
                    <p className="text-xs font-semibold text-slate-700">
                      Click to browse or drag and drop scanned FDR copy
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Supports PDF, JPG, PNG (Max 10MB) • Verified via binary signature
                    </p>
                  </>
                )}
              </div>
            </div>

            {fileError && (
              <p className="text-xs text-danger font-medium">{fileError}</p>
            )}

            <div className="flex items-center space-x-2 pt-2">
              <input
                type="checkbox"
                id="autoSubmitScrutiny"
                checked={autoSubmitScrutiny}
                onChange={(e) => setAutoSubmitScrutiny(e.target.checked)}
                className="w-4 h-4 text-primary rounded border-slate-300 focus:ring-primary"
              />
              <label htmlFor="autoSubmitScrutiny" className="text-xs text-slate-700 cursor-pointer">
                Automatically submit for AICTE Scrutiny upon upload (moves from Draft to Under Scrutiny)
              </label>
            </div>
          </div>

        </form>

        {/* Modal Footer */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg hover:bg-slate-200 transition"
          >
            Cancel
          </button>

          <button
            id="fdr-save-submit-btn"
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-6 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-2 disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Processing Submission...</span>
              </>
            ) : (
              <>
                <span>Save &amp; Register FDR</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}

