import React, { useState, useEffect, useRef } from 'react';
import { 
  Bell, 
  Check, 
  CheckCheck, 
  AlertTriangle, 
  AlertCircle, 
  Clock, 
  ExternalLink, 
  RefreshCw,
  Mail,
  Smartphone,
  ShieldAlert,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { notificationService } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function NotificationBellDropdown({ onSelectFDR }) {
  const { user, role } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('ALL'); // ALL, UNREAD, ESCALATION, MATURITY_ALERT
  const [markingAll, setMarkingAll] = useState(false);
  const [scanning, setScanning] = useState(false);

  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const params = {};
      if (activeTab === 'UNREAD') {
        params.unread_only = true;
      } else if (activeTab === 'ESCALATION') {
        params.category = 'ESCALATION';
      } else if (activeTab === 'MATURITY_ALERT') {
        params.category = 'MATURITY_ALERT';
      }

      const res = await notificationService.getNotifications(params);
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
      setTotalCount(res.total_count || 0);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll every 30 seconds for live notification updates
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [user, activeTab]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkAsRead = async (id, e) => {
    e.stopPropagation();
    try {
      await notificationService.markAsRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Error marking read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Error marking all read:", err);
    } finally {
      setMarkingAll(false);
    }
  };

  const handleTriggerEscalationScan = async () => {
    setScanning(true);
    try {
      const res = await notificationService.triggerEscalation();
      alert(`Escalation & Maturity Scan Complete!\nScanned Instruments: ${res.scanned_fdrs}\nEscalations Logged: ${res.escalations_triggered}\nAlerts Dispatched: ${res.notifications_dispatched}`);
      fetchNotifications();
    } catch (err) {
      console.error("Scan error:", err);
      alert("Failed to execute escalation scan.");
    } finally {
      setScanning(false);
    }
  };

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'WARNING':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'INFO':
      default:
        return 'bg-blue-100 text-primary border-blue-200';
    }
  };

  const getChannelBadge = (ch) => {
    switch (ch) {
      case 'EMAIL_SIMULATED':
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
            <Mail className="w-2.5 h-2.5 text-blue-600" />
            <span>Email Sent</span>
          </span>
        );
      case 'SMS_SIMULATED':
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
            <Smartphone className="w-2.5 h-2.5 text-emerald-600" />
            <span>SMS Sent</span>
          </span>
        );
      case 'IN_APP':
      default:
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
            <Bell className="w-2.5 h-2.5 text-slate-500" />
            <span>In-App</span>
          </span>
        );
    }
  };

  const canTriggerEscalation = ['ROLE_SYSTEM_ADMIN', 'ROLE_APPROVING_AUTHORITY', 'ROLE_SCRUTINY_OFFICER'].includes(role);

  return (
    <div className="relative" ref={dropdownRef}>
      
      {/* Bell Trigger Button */}
      <button
        id="notification-bell-btn"
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-slate-600 hover:text-primary hover:bg-slate-100 rounded-lg transition"
        title="Regulatory Alerts & Escalations"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex items-center justify-center rounded-full h-4 w-4 bg-rose-600 text-[9px] font-bold text-white">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 md:w-[450px] bg-white rounded-xl shadow-2xl border border-slate-200 z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
          
          {/* Header */}
          <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 bg-primary text-white rounded-lg flex items-center justify-center font-bold text-xs shadow-xs">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-800">Alerts &amp; Escalations</h4>
                <p className="text-[10px] text-slate-500">
                  {unreadCount} unread notification{unreadCount === 1 ? '' : 's'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  disabled={markingAll}
                  className="flex items-center space-x-1 text-[11px] text-primary hover:text-primary-dark font-medium transition"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Mark all read</span>
                </button>
              )}
              <button
                onClick={fetchNotifications}
                disabled={loading}
                className="p-1 text-slate-500 hover:text-slate-800 rounded transition"
                title="Refresh feed"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center px-3 pt-2 border-b border-slate-200 bg-white text-[11px] font-medium space-x-2 overflow-x-auto">
            <button
              onClick={() => setActiveTab('ALL')}
              className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                activeTab === 'ALL' ? 'border-primary text-primary font-bold' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              All ({totalCount})
            </button>
            <button
              onClick={() => setActiveTab('UNREAD')}
              className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                activeTab === 'UNREAD' ? 'border-primary text-primary font-bold' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Unread ({unreadCount})
            </button>
            <button
              onClick={() => setActiveTab('ESCALATION')}
              className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                activeTab === 'ESCALATION' ? 'border-primary text-primary font-bold' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Escalations
            </button>
            <button
              onClick={() => setActiveTab('MATURITY_ALERT')}
              className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                activeTab === 'MATURITY_ALERT' ? 'border-primary text-primary font-bold' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Maturity (90/60/30/15/7d)
            </button>
          </div>

          {/* Notifications List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 bg-white">
            {loading && notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <RefreshCw className="w-5 h-5 mx-auto animate-spin mb-2 text-primary" />
                <span>Loading notifications...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
                <p className="font-semibold text-slate-600">All caught up!</p>
                <p className="text-[11px] mt-0.5">No alerts matching active filter.</p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`p-3.5 transition flex items-start space-x-3 text-left ${
                    !item.is_read ? 'bg-blue-50/40 border-l-4 border-primary' : 'hover:bg-slate-50'
                  }`}
                >
                  {/* Category / Severity Icon */}
                  <div className="mt-0.5 flex-shrink-0">
                    {item.category === 'ESCALATION' ? (
                      <div className="w-6 h-6 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center">
                        <ShieldAlert className="w-3.5 h-3.5" />
                      </div>
                    ) : item.severity === 'CRITICAL' || item.severity === 'HIGH' ? (
                      <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center">
                        <AlertTriangle className="w-3.5 h-3.5" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-blue-100 text-primary flex items-center justify-center">
                        <AlertCircle className="w-3.5 h-3.5" />
                      </div>
                    )}
                  </div>

                  {/* Body Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-1.5 flex-wrap gap-y-1 mb-1">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getSeverityBadge(item.severity)}`}>
                        {item.severity}
                      </span>
                      {item.escalation_level > 0 && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-600 text-white shadow-xs">
                          Tier {item.escalation_level}
                        </span>
                      )}
                      {getChannelBadge(item.channel)}
                      <span className="text-[10px] text-slate-400 ml-auto flex items-center space-x-1">
                        <Clock className="w-2.5 h-2.5" />
                        <span>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </span>
                    </div>

                    <h5 className={`text-xs font-bold leading-snug ${!item.is_read ? 'text-slate-900' : 'text-slate-700'}`}>
                      {item.title}
                    </h5>
                    
                    <p className="text-[11px] text-slate-600 mt-1 leading-relaxed break-words">
                      {item.message}
                    </p>

                    <div className="mt-2 flex items-center justify-between text-xs pt-1">
                      {item.fdr_id && onSelectFDR ? (
                        <button
                          onClick={() => {
                            setIsOpen(false);
                            onSelectFDR(item.fdr_id);
                          }}
                          className="inline-flex items-center space-x-1 text-[11px] text-primary hover:text-primary-dark font-semibold"
                        >
                          <span>Inspect Instrument #{item.fdr_id}</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      ) : <span />}

                      {!item.is_read && (
                        <button
                          onClick={(e) => handleMarkAsRead(item.id, e)}
                          className="inline-flex items-center space-x-1 text-[10px] text-slate-500 hover:text-slate-800 bg-white hover:bg-slate-100 border border-slate-200 px-2 py-0.5 rounded transition"
                          title="Mark as read"
                        >
                          <Check className="w-2.5 h-2.5 text-emerald-600" />
                          <span>Mark read</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer with Administrator Escalation Trigger */}
          {canTriggerEscalation && (
            <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[10px] text-slate-500 font-medium">
                Admin Automation Controls
              </span>
              <button
                id="trigger-escalation-scan-btn"
                onClick={handleTriggerEscalationScan}
                disabled={scanning}
                className="flex items-center space-x-1.5 text-[11px] bg-primary hover:bg-primary-dark text-white font-medium px-2.5 py-1 rounded-md shadow-xs transition disabled:opacity-50"
              >
                <Sparkles className={`w-3 h-3 ${scanning ? 'animate-spin' : ''}`} />
                <span>{scanning ? 'Running Scan...' : 'Trigger Escalation Scan'}</span>
              </button>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
