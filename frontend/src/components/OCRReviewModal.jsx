import React, { useState, useEffect } from 'react';
import { 
  X, 
  Sparkles, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Download, 
  Eye, 
  Save, 
  Cpu, 
  Clock, 
  ShieldCheck, 
  Building2, 
  DollarSign, 
  Calendar,
  Layers,
  ChevronRight
} from 'lucide-react';
import { ocrService, documentService } from '../services/api';

export default function OCRReviewModal({ fdr, isOpen, onClose, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [extraction, setExtraction] = useState(null);
  const [activeTab, setActiveTab] = useState('fields'); // 'fields', 'raw'
  const [docPreviewUrl, setDocPreviewUrl] = useState(null);
  const [docMimeType, setDocMimeType] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Editable fields state
  const [fields, setFields] = useState({
    fdr_number: '',
    bank_name: '',
    branch_name: '',
    ifsc_code: '',
    deposit_amount: '',
    issue_date: '',
    maturity_date: '',
    interest_rate: '',
    beneficiary: ''
  });

  useEffect(() => {
    if (isOpen && fdr) {
      loadDocumentPreview();
      loadExtractionData();
    }
  }, [isOpen, fdr]);

  const loadDocumentPreview = async () => {
    if (!fdr.documents || fdr.documents.length === 0) return;
    const doc = fdr.documents[0];
    try {
      const { blobUrl, mimeType } = await documentService.getPreviewBlob(doc.id);
      setDocPreviewUrl(blobUrl);
      setDocMimeType(mimeType);
    } catch (e) {
      console.warn("Could not load direct preview blob:", e);
    }
  };

  const loadExtractionData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ocrService.getExtraction(fdr.id);
      setExtraction(data);
      if (data && data.extracted_fields) {
        setFields({
          fdr_number: data.extracted_fields.fdr_number || fdr.fdr_number || '',
          bank_name: data.extracted_fields.bank_name || fdr.bank_name || '',
          branch_name: data.extracted_fields.branch_name || fdr.branch_name || '',
          ifsc_code: data.extracted_fields.ifsc_code || fdr.ifsc_code || '',
          deposit_amount: data.extracted_fields.deposit_amount || fdr.deposit_amount || '',
          issue_date: data.extracted_fields.issue_date || fdr.issue_date || '',
          maturity_date: data.extracted_fields.maturity_date || fdr.maturity_date || '',
          interest_rate: data.extracted_fields.interest_rate || fdr.interest_rate || '',
          beneficiary: data.extracted_fields.beneficiary || fdr.beneficiary || ''
        });
      }
    } catch (err) {
      // 404 indicates OCR hasn't been triggered yet
      setExtraction(null);
      // Pre-populate with FDR record values
      setFields({
        fdr_number: fdr.fdr_number || '',
        bank_name: fdr.bank_name || '',
        branch_name: fdr.branch_name || '',
        ifsc_code: fdr.ifsc_code || '',
        deposit_amount: fdr.deposit_amount || '',
        issue_date: fdr.issue_date || '',
        maturity_date: fdr.maturity_date || '',
        interest_rate: fdr.interest_rate || '',
        beneficiary: fdr.beneficiary || ''
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRunExtraction = async () => {
    setExtracting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const result = await ocrService.extract(fdr.id);
      setExtraction(result);
      if (result.extracted_fields) {
        setFields(prev => ({
          ...prev,
          ...result.extracted_fields
        }));
      }
      setSuccessMessage("AI OCR extraction completed with structured field confidence scoring.");
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Extraction error:", err);
      setError(err.response?.data?.detail || "OCR Extraction failed. You may enter data manually.");
    } finally {
      setExtracting(false);
    }
  };

  const handleApplyCorrections = async () => {
    setSaving(true);
    setError(null);
    try {
      await ocrService.reviewAndCorrect(fdr.id, fields);
      setSuccessMessage("Verified field values successfully applied to FDR statutory record.");
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Save error:", err);
      setError(err.response?.data?.detail || "Failed to update FDR fields.");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen || !fdr) return null;

  const confidences = extraction?.field_confidences || {};
  const overallConf = extraction?.overall_confidence || 0;

  const getConfBadge = (fieldKey) => {
    const score = confidences[fieldKey];
    if (score === undefined || score === null) {
      return (
        <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-semibold">
          Manual / Unscored
        </span>
      );
    }
    if (score >= 90) {
      return (
        <span className="text-[10px] bg-emerald-50 text-success border border-emerald-200 px-2 py-0.5 rounded-full font-bold flex items-center space-x-1">
          <CheckCircle2 className="w-3 h-3" />
          <span>{score}% High</span>
        </span>
      );
    }
    if (score >= 70) {
      return (
        <span className="text-[10px] bg-amber-50 text-warning border border-amber-200 px-2 py-0.5 rounded-full font-bold flex items-center space-x-1">
          <AlertTriangle className="w-3 h-3" />
          <span>{score}% Medium</span>
        </span>
      );
    }
    return (
      <span className="text-[10px] bg-red-50 text-danger border border-red-200 px-2 py-0.5 rounded-full font-bold flex items-center space-x-1">
        <AlertTriangle className="w-3 h-3" />
        <span>{score}% Low</span>
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-7xl h-[94vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Top Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary text-white rounded-xl flex items-center justify-center shadow-xs">
              <Sparkles className="w-5 h-5 text-blue-200" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-800">
                  AI-Powered OCR Document Intelligence &amp; Review Desk
                </h3>
                {overallConf > 0 && (
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                    overallConf >= 90 ? 'bg-emerald-50 text-success border-emerald-200' : 'bg-amber-50 text-warning border-amber-200'
                  }`}>
                    {overallConf}% Overall Confidence
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Instrument: <span className="font-mono font-semibold text-primary">{fdr.fdr_number}</span> ({fdr.bank_name}) • Review draft extractions before final scrutiny
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              id="run-ocr-btn"
              onClick={handleRunExtraction}
              disabled={extracting}
              className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-4 py-2 rounded-lg transition shadow-xs flex items-center space-x-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${extracting ? 'animate-spin' : ''}`} />
              <span>{extracting ? 'Extracting OCR...' : 'Run OCR Extraction'}</span>
            </button>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Alert Banners */}
        {error && (
          <div className="bg-red-50 border-b border-red-200 px-6 py-2.5 flex items-center space-x-2 text-xs text-danger">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-2.5 flex items-center space-x-2 text-xs text-success">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Split View Content Area */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 overflow-hidden">
          
          {/* LEFT COLUMN: Document Visual Inspector (55% width) */}
          <div className="md:col-span-7 border-r border-slate-200 bg-slate-100/70 flex flex-col h-full overflow-hidden">
            <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-slate-500" />
                <span className="font-semibold text-slate-700">
                  {fdr.documents?.[0]?.original_filename || 'FDR Scanned Instrument'}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  ({(fdr.documents?.[0]?.file_size / 1024).toFixed(1) || 0} KB)
                </span>
              </div>

              {fdr.documents?.[0] && (
                <button
                  onClick={() => documentService.downloadWithAuth(fdr.documents[0].id, fdr.documents[0].original_filename)}
                  className="flex items-center space-x-1 text-[11px] text-slate-600 hover:text-primary transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </button>
              )}
            </div>

            {/* Document Render Area */}
            <div className="flex-1 p-4 overflow-y-auto flex items-center justify-center">
              {docPreviewUrl ? (
                docMimeType === 'application/pdf' ? (
                  <iframe
                    src={`${docPreviewUrl}#toolbar=0`}
                    title="Document Preview"
                    className="w-full h-full rounded-xl bg-white shadow-subtle border border-slate-200"
                  />
                ) : (
                  <img
                    src={docPreviewUrl}
                    alt="Document Scan"
                    className="max-h-full max-w-full object-contain rounded-xl shadow-subtle border border-slate-200 bg-white"
                  />
                )
              ) : (
                <div className="text-center p-8 text-slate-400 space-y-2">
                  <FileText className="w-12 h-12 mx-auto text-slate-300" />
                  <p className="text-xs">Document preview loading or not available.</p>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: Extracted Fields & Confidence Scorecard (45% width) */}
          <div className="md:col-span-5 bg-white flex flex-col h-full overflow-hidden">
            
            {/* Metadata Ribbon */}
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-primary" />
                <span className="font-semibold text-slate-700">
                  {extraction?.processing_engine || 'PyMuPDF + OpenCV + Tesseract'}
                </span>
              </div>

              {extraction?.processing_time_ms && (
                <span className="text-[11px] text-slate-500 font-mono flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{extraction.processing_time_ms} ms</span>
                </span>
              )}
            </div>

            {/* Fields Form */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              
              <div className="text-xs text-slate-500 leading-relaxed bg-blue-50/50 p-3 rounded-lg border border-blue-100">
                <span className="font-semibold text-primary">Human-in-the-Loop Review:</span> Verify the AI-extracted fields against the document on the left. You may adjust any value before saving.
              </div>

              {/* Field 1: FDR Number */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">FDR Certificate Number</label>
                  {getConfBadge('fdr_number')}
                </div>
                <input
                  id="ocr-field-fdr-number"
                  type="text"
                  value={fields.fdr_number}
                  onChange={(e) => setFields(prev => ({ ...prev, fdr_number: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md font-mono font-semibold text-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Field 2: Issuing Bank */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Issuing Bank</label>
                  {getConfBadge('bank_name')}
                </div>
                <input
                  type="text"
                  value={fields.bank_name}
                  onChange={(e) => setFields(prev => ({ ...prev, bank_name: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md text-slate-800 font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Field 3: Branch Name */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Branch Location</label>
                  {getConfBadge('branch_name')}
                </div>
                <input
                  type="text"
                  value={fields.branch_name}
                  onChange={(e) => setFields(prev => ({ ...prev, branch_name: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Field 4: IFSC Code */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Bank IFSC Code</label>
                  {getConfBadge('ifsc_code')}
                </div>
                <input
                  type="text"
                  maxLength={11}
                  value={fields.ifsc_code}
                  onChange={(e) => setFields(prev => ({ ...prev, ifsc_code: e.target.value.toUpperCase() }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md font-mono uppercase text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Field 5: Deposit Amount */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Principal Deposit Amount (₹)</label>
                  {getConfBadge('deposit_amount')}
                </div>
                <input
                  id="ocr-field-amount"
                  type="number"
                  value={fields.deposit_amount}
                  onChange={(e) => setFields(prev => ({ ...prev, deposit_amount: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md font-semibold text-slate-900 focus:outline-none focus:ring-1 focus:ring-primary"
                />
                {fields.deposit_amount && (
                  <span className="text-[10px] text-slate-500 font-mono">
                    Formatted: ₹ {Number(fields.deposit_amount).toLocaleString('en-IN')}
                  </span>
                )}
              </div>

              {/* Field 6 & 7: Dates */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-slate-700">Issue Date</label>
                    {getConfBadge('issue_date')}
                  </div>
                  <input
                    type="date"
                    value={fields.issue_date}
                    onChange={(e) => setFields(prev => ({ ...prev, issue_date: e.target.value }))}
                    className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-slate-700">Maturity Date</label>
                    {getConfBadge('maturity_date')}
                  </div>
                  <input
                    type="date"
                    value={fields.maturity_date}
                    onChange={(e) => setFields(prev => ({ ...prev, maturity_date: e.target.value }))}
                    className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Field 8: Interest Rate */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Annual Interest Rate (% p.a.)</label>
                  {getConfBadge('interest_rate')}
                </div>
                <input
                  type="number"
                  step="0.05"
                  value={fields.interest_rate}
                  onChange={(e) => setFields(prev => ({ ...prev, interest_rate: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Field 9: Beneficiary */}
              <div className="p-3 rounded-lg border border-slate-200 bg-white hover:border-primary/40 transition space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-700">Beneficiary Authority</label>
                  {getConfBadge('beneficiary')}
                </div>
                <input
                  type="text"
                  value={fields.beneficiary}
                  onChange={(e) => setFields(prev => ({ ...prev, beneficiary: e.target.value }))}
                  className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-md bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

            </div>

            {/* Bottom Action Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <button
                type="button"
                onClick={onClose}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-3 py-2 rounded-lg hover:bg-slate-200 transition"
              >
                Close
              </button>

              <button
                id="apply-ocr-corrections-btn"
                onClick={handleApplyCorrections}
                disabled={saving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? 'Saving Changes...' : 'Confirm & Apply Verified Values'}</span>
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}

