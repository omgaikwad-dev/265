import React, { useState } from 'react';
import { 
  X, 
  FileText, 
  Download, 
  Calendar, 
  Building2, 
  ShieldCheck, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Upload, 
  RefreshCw,
  Hash,
  Send,
  Eye
} from 'lucide-react';
import { fdrService, documentService } from '../services/api';

export default function FDRDetailModal({ fdr, isOpen, onClose, onRefresh, currentRole, onOpenOCR, onOpenVerification, onOpenRenewal, onOpenRelease }) {
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [submittingScrutiny, setSubmittingScrutiny] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  if (!isOpen || !fdr) return null;

  const handleDownload = async (doc) => {
    try {
      await documentService.downloadWithAuth(doc.id, doc.original_filename);
    } catch (e) {
      console.error("Download failed:", e);
      alert("Failed to download document. Please ensure you have sufficient permissions.");
    }
  };

  const handleAddDocument = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setActionError(null);
    setUploadingDoc(true);
    try {
      await fdrService.uploadDocument(fdr.id, file, "SUPPORTING");
      setActionSuccess("Document uploaded successfully.");
      onRefresh();
    } catch (err) {
      console.error("Upload error:", err);
      setActionError(err.response?.data?.detail || "Failed to upload document.");
    } finally {
      setUploadingDoc(false);
    }
  };

  const handleSubmitForScrutiny = async () => {
    setActionError(null);
    setSubmittingScrutiny(true);
    try {
      await fdrService.submitForScrutiny(fdr.id);
      setActionSuccess("FDR successfully submitted for AICTE Scrutiny.");
      onRefresh();
    } catch (err) {
      console.error("Submit error:", err);
      setActionError(err.response?.data?.detail || "Failed to submit FDR for scrutiny.");
    } finally {
      setSubmittingScrutiny(false);
    }
  };

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

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary text-white rounded-xl flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold font-mono text-primary">{fdr.fdr_number}</h3>
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${getStatusBadge(fdr.lifecycle_status)}`}>
                  {fdr.lifecycle_status}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {fdr.bank_name} • {fdr.branch_name} (IFSC: <span className="font-mono">{fdr.ifsc_code}</span>)
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

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {actionError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-danger flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{actionError}</span>
            </div>
          )}

          {actionSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-success flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {/* Financial Metrics Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400">Principal Amount</span>
              <div className="text-xl font-bold text-slate-800 mt-1">
                ₹ {Number(fdr.deposit_amount).toLocaleString('en-IN')}
              </div>
              <span className="text-[10px] text-slate-500">Fixed Deposit Principal</span>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400">Annual Interest</span>
              <div className="text-xl font-bold text-primary mt-1">
                {fdr.interest_rate ? `${fdr.interest_rate} %` : 'N/A'}
              </div>
              <span className="text-[10px] text-slate-500">Rate of return p.a.</span>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400">Issuance Date</span>
              <div className="text-base font-bold text-slate-800 mt-1 font-mono">
                {fdr.issue_date}
              </div>
              <span className="text-[10px] text-slate-500">Start of deposit</span>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400">Maturity Date</span>
              <div className="text-base font-bold text-slate-800 mt-1 font-mono">
                {fdr.maturity_date}
              </div>
              <span className="text-[10px] text-slate-500">Scheduled maturity</span>
            </div>
          </div>

          {/* Instrument Particulars */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wide text-slate-700 pb-2 border-b border-slate-100 flex items-center space-x-1.5">
              <Building2 className="w-3.5 h-3.5 text-primary" />
              <span>Statutory Ownership &amp; Verification Attributes</span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400">AICTE Permanent ID:</span>
                <span className="font-mono font-semibold text-slate-800 ml-2">{fdr.aicte_id || 'AICTE-1-98765432'}</span>
              </div>
              <div>
                <span className="text-slate-400">Institution:</span>
                <span className="font-semibold text-slate-800 ml-2">{fdr.institution_name || 'Delhi Institute of Technology & Advanced Studies'}</span>
              </div>
              <div>
                <span className="text-slate-400">Beneficiary:</span>
                <span className="font-semibold text-slate-800 ml-2">{fdr.beneficiary}</span>
              </div>
              <div>
                <span className="text-slate-400">Joint Holder:</span>
                <span className="font-semibold text-slate-800 ml-2">{fdr.joint_holder || 'Not Specified'}</span>
              </div>
              <div>
                <span className="text-slate-400">OCR Extraction Status:</span>
                <span className="font-semibold text-primary ml-2 uppercase">{fdr.ocr_status}</span>
              </div>
              <div>
                <span className="text-slate-400">Verification Engine Status:</span>
                <span className="font-semibold text-success ml-2 uppercase">{fdr.verification_status}</span>
              </div>
            </div>
          </div>

          {/* Attached Documents Vault */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-700 flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                <span>Cryptographically Verified Supporting Documents ({fdr.documents?.length || 0})</span>
              </h4>

              {/* Upload Additional Document Trigger */}
              <label className="cursor-pointer bg-secondary hover:bg-secondary-hover text-primary font-semibold text-[11px] px-2.5 py-1 rounded-md border border-blue-200 transition flex items-center space-x-1">
                <Upload className="w-3 h-3" />
                <span>{uploadingDoc ? 'Uploading...' : 'Attach Document'}</span>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleAddDocument}
                  disabled={uploadingDoc}
                  className="hidden"
                />
              </label>
            </div>

            <div className="space-y-2">
              {fdr.documents && fdr.documents.length > 0 ? (
                fdr.documents.map((doc) => (
                  <div key={doc.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between hover:bg-slate-100/60 transition">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-100 text-primary rounded-lg flex items-center justify-center">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-semibold text-xs text-slate-800">{doc.original_filename}</div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5 flex items-center space-x-2">
                          <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span>SHA-256: {doc.sha256_hash.slice(0, 16)}...</span>
                          <span>•</span>
                          <span className="uppercase text-slate-600 font-semibold">{doc.document_type}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleDownload(doc)}
                        className="flex items-center space-x-1 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium px-2.5 py-1.5 rounded-md border border-slate-200 transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
                  No documents attached yet. You must upload at least one scanned instrument copy before submitting for scrutiny.
                </div>
              )}
            </div>
          </div>

          {/* Remarks Section */}
          {(fdr.scrutiny_remarks || fdr.authority_remarks) && (
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2 text-xs">
              <h4 className="font-bold text-slate-700 uppercase tracking-wide text-[10px]">Official Scrutiny &amp; Statutory Notes</h4>
              {fdr.scrutiny_remarks && (
                <p className="text-slate-600"><strong>Scrutiny Officer:</strong> {fdr.scrutiny_remarks}</p>
              )}
              {fdr.authority_remarks && (
                <p className="text-slate-600"><strong>Approving Authority:</strong> {fdr.authority_remarks}</p>
              )}
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg hover:bg-slate-200 transition"
            >
              Close
            </button>
            <button
              id="open-ocr-modal-btn"
              onClick={() => {
                onClose();
                if (onOpenOCR) onOpenOCR(fdr);
              }}
              className="bg-secondary hover:bg-secondary-hover text-primary font-semibold text-xs px-3.5 py-2 rounded-lg border border-blue-200 transition flex items-center space-x-1.5"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>AI OCR Extraction</span>
            </button>
            <button
              id="open-verification-modal-btn"
              onClick={() => {
                onClose();
                if (onOpenVerification) onOpenVerification(fdr);
              }}
              className="bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-xs px-3.5 py-2 rounded-lg border border-amber-200 transition flex items-center space-x-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
              <span>12-Rule Verification</span>
            </button>
          </div>

          {fdr.lifecycle_status === 'DRAFT' && currentRole === 'ROLE_INSTITUTION_ADMIN' && (
            <button
              id="fdr-submit-scrutiny-btn"
              onClick={handleSubmitForScrutiny}
              disabled={submittingScrutiny}
              className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-2 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submittingScrutiny ? 'Submitting...' : 'Submit for AICTE Scrutiny'}</span>
            </button>
          )}

          {['APPROVED_ACTIVE', 'RENEWAL_DUE', 'MATURED'].includes(fdr.lifecycle_status) && currentRole === 'ROLE_INSTITUTION_ADMIN' && (
            <div className="flex items-center space-x-2">
              <button
                id="fdr-initiate-renewal-btn"
                onClick={() => {
                  onClose();
                  if (onOpenRenewal) onOpenRenewal(fdr);
                }}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg transition shadow-sm flex items-center space-x-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Initiate Renewal</span>
              </button>
              <button
                id="fdr-request-release-btn"
                onClick={() => {
                  onClose();
                  if (onOpenRelease) onOpenRelease(fdr);
                }}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg transition shadow-sm flex items-center space-x-1.5"
              >
                <span>Request Release / Refund</span>
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

