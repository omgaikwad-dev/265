import React, { useState } from 'react';
import { 
  Building2, 
  User, 
  Mail, 
  Phone, 
  MapPin, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  ArrowLeft, 
  ShieldCheck,
  FileCheck
} from 'lucide-react';
import { authService } from '../services/api';

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
  "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", 
  "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", 
  "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", 
  "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", 
  "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
];

export default function RegisterInstitution({ onNavigateToLogin }) {
  const [formData, setFormData] = useState({
    aicte_id: 'AICTE-1-' + Math.floor(10000000 + Math.random() * 90000000),
    name: '',
    institution_type: 'Engineering & Technology',
    address: '',
    state: 'Maharashtra',
    district: '',
    pin_code: '',
    official_email: '',
    phone_number: '',
    admin_name: '',
    admin_username: '',
    admin_email: '',
    admin_phone: '',
    admin_designation: 'Registrar / FDR Custodian',
    password: '',
    confirm_password: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirm_password) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        aicte_id: formData.aicte_id,
        name: formData.name,
        institution_type: formData.institution_type,
        address: formData.address,
        state: formData.state,
        district: formData.district,
        pin_code: formData.pin_code,
        official_email: formData.official_email,
        phone_number: formData.phone_number,
        admin_name: formData.admin_name,
        admin_username: formData.admin_username,
        admin_email: formData.admin_email,
        admin_phone: formData.admin_phone,
        admin_designation: formData.admin_designation,
        password: formData.password
      };
      await authService.registerInstitution(payload);
      setSuccess(true);
    } catch (err) {
      console.error("Registration error:", err);
      setError(
        err.response?.data?.detail || "Registration failed. Please verify the provided details."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-elevated border border-slate-200 p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-emerald-100 text-success rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-9 h-9" />
          </div>
          <h3 className="text-xl font-bold text-slate-800">Institution Registered!</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Your institution record <span className="font-semibold text-primary">{formData.aicte_id}</span> has been provisioned and is ready for FDR submissions.
          </p>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-left space-y-1 font-mono text-slate-700">
            <div><strong>AICTE ID:</strong> {formData.aicte_id}</div>
            <div><strong>Admin Login:</strong> {formData.admin_username}</div>
            <div><strong>Admin Email:</strong> {formData.admin_email}</div>
          </div>
          <button
            id="login-after-reg-btn"
            onClick={onNavigateToLogin}
            className="w-full bg-primary hover:bg-primary-dark text-white font-semibold text-xs py-2.5 rounded-lg transition shadow-sm"
          >
            Proceed to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto my-8 p-4">
      <div className="bg-white rounded-2xl shadow-card border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className="bg-primary text-white p-6 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold">New Institution Onboarding</h2>
              <p className="text-xs text-blue-100">AICTE Security Deposit &amp; FDR Management System</p>
            </div>
          </div>
          <button
            onClick={onNavigateToLogin}
            className="text-xs text-blue-100 hover:text-white flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-white/10 border border-white/20 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Login</span>
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="m-6 mb-0 p-3.5 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2.5 text-xs text-danger">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          
          {/* Section 1: Institutional Details */}
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-800 pb-2 border-b border-slate-100 flex items-center space-x-2">
              <span className="w-5 h-5 bg-blue-100 text-primary rounded-full flex items-center justify-center text-xs">1</span>
              <span>Institution Identification &amp; Campus Location</span>
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  AICTE Permanent / Application ID *
                </label>
                <input
                  id="reg-aicte-id"
                  type="text"
                  name="aicte_id"
                  value={formData.aicte_id}
                  onChange={handleChange}
                  required
                  placeholder="e.g. AICTE-1-10023456"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Institution Discipline / Category
                </label>
                <select
                  name="institution_type"
                  value={formData.institution_type}
                  onChange={handleChange}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white"
                >
                  <option value="Engineering & Technology">Engineering &amp; Technology</option>
                  <option value="Management Studies">Management Studies</option>
                  <option value="Pharmacy">Pharmacy</option>
                  <option value="Architecture & Planning">Architecture &amp; Planning</option>
                  <option value="Applied Arts & Crafts">Applied Arts &amp; Crafts</option>
                  <option value="Hotel Management & Catering">Hotel Management &amp; Catering</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Institution Name *
                </label>
                <input
                  id="reg-name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Maharashtra Institute of Technology & Research"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Campus Address *
                </label>
                <input
                  id="reg-address"
                  type="text"
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  required
                  placeholder="Survey No., Street, Sector, Landmark"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">State *</label>
                <select
                  name="state"
                  value={formData.state}
                  onChange={handleChange}
                  required
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white"
                >
                  {INDIAN_STATES.map(st => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">District *</label>
                <input
                  id="reg-district"
                  type="text"
                  name="district"
                  value={formData.district}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Pune / Mumbai / Delhi"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Official Institution Email *</label>
                <input
                  id="reg-inst-email"
                  type="email"
                  name="official_email"
                  value={formData.official_email}
                  onChange={handleChange}
                  required
                  placeholder="registrar@institution.edu.in"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Official Telephone / Mobile *</label>
                <input
                  id="reg-inst-phone"
                  type="text"
                  name="phone_number"
                  value={formData.phone_number}
                  onChange={handleChange}
                  required
                  placeholder="+91 22 2456 7890"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Administrator Account Details */}
          <div className="space-y-4 pt-4 border-t border-slate-100">
            <h4 className="text-sm font-bold text-slate-800 pb-2 border-b border-slate-100 flex items-center space-x-2">
              <span className="w-5 h-5 bg-blue-100 text-primary rounded-full flex items-center justify-center text-xs">2</span>
              <span>Designated Institution Administrator Account (ROLE_INSTITUTION_ADMIN)</span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Full Name *</label>
                <input
                  id="reg-admin-name"
                  type="text"
                  name="admin_name"
                  value={formData.admin_name}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Dr. Rajeshwar Sharma"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Username *</label>
                <input
                  id="reg-admin-username"
                  type="text"
                  name="admin_username"
                  value={formData.admin_username}
                  onChange={handleChange}
                  required
                  placeholder="e.g. rsharma_admin"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Email *</label>
                <input
                  id="reg-admin-email"
                  type="email"
                  name="admin_email"
                  value={formData.admin_email}
                  onChange={handleChange}
                  required
                  placeholder="admin.fdr@institution.edu.in"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Mobile</label>
                <input
                  type="text"
                  name="admin_phone"
                  value={formData.admin_phone}
                  onChange={handleChange}
                  placeholder="+91 98765 43210"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Password *</label>
                <input
                  id="reg-password"
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="Minimum 6 characters"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm Password *</label>
                <input
                  id="reg-confirm-password"
                  type="password"
                  name="confirm_password"
                  value={formData.confirm_password}
                  onChange={handleChange}
                  required
                  placeholder="Re-enter password"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">* All starred fields are mandatory for statutory verification</span>
            <button
              id="submit-registration-btn"
              type="submit"
              disabled={submitting}
              className="bg-primary hover:bg-primary-dark text-white font-semibold text-xs px-6 py-2.5 rounded-lg transition shadow-sm flex items-center space-x-2 disabled:opacity-50"
            >
              <span>{submitting ? 'Registering...' : 'Submit Institutional Registration'}</span>
              <FileCheck className="w-4 h-4" />
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
