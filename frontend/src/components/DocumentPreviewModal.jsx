import React, { useState, useEffect } from 'react';
import { X, Download, FileText, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { documentService } from '../services/api';

export default function DocumentPreviewModal({ documentId, filename, onClose }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [mimeType, setMimeType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    let createdUrl = null;

    const fetchPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        const { blobUrl: url, mimeType: type } = await documentService.getPreviewBlob(documentId);
        if (active) {
          createdUrl = url;
          setBlobUrl(url);
          setMimeType(type);
        }
      } catch (err) {
        if (active) {
          setError(err.response?.data?.detail || "Failed to load document preview.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    if (documentId) {
      fetchPreview();
    }

    return () => {
      active = false;
      if (createdUrl) {
        window.URL.revokeObjectURL(createdUrl);
      }
    };
  }, [documentId]);

  const handleDownload = () => {
    documentService.downloadWithAuth(documentId, filename);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-100 text-primary flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 truncate max-w-md">{filename || "Document Viewer"}</h3>
              <p className="text-[11px] text-slate-500 font-mono">Document Vault Reference ID: #{documentId}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownload}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 rounded-lg transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="flex-1 bg-slate-100 p-4 min-h-[450px] overflow-auto flex items-center justify-center">
          {loading && (
            <div className="flex flex-col items-center space-y-2 text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <p className="text-xs">Decrypting and streaming document securely...</p>
            </div>
          )}

          {error && (
            <div className="bg-white p-6 rounded-xl border border-red-200 text-center max-w-md shadow-sm">
              <AlertCircle className="w-10 h-10 text-danger mx-auto mb-2" />
              <h4 className="text-sm font-bold text-slate-800">Preview Unavailable</h4>
              <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
              <button
                onClick={handleDownload}
                className="inline-flex items-center space-x-1.5 px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-primary-dark transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Try Direct Download</span>
              </button>
            </div>
          )}

          {!loading && !error && blobUrl && (
            <div className="w-full h-full min-h-[550px] flex items-center justify-center">
              {mimeType === 'application/pdf' ? (
                <iframe
                  src={`${blobUrl}#toolbar=0`}
                  title="PDF Preview"
                  className="w-full h-[550px] rounded-lg border border-slate-200 bg-white shadow-xs"
                />
              ) : (
                <img
                  src={blobUrl}
                  alt="Document Preview"
                  className="max-h-[550px] max-w-full rounded-lg object-contain shadow-xs border border-slate-200"
                />
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
          <span>AICTE Security Deposit Vault • Access Controlled &amp; Audited</span>
          <span>Classification: Statutory Evidence</span>
        </div>

      </div>
    </div>
  );
}
