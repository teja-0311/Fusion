/**
 * RSPC Notifications System Frontend Components (UC-015)
 * 
 * Components:
 * 1. NotificationBell - Icon in navbar with unread count badge
 * 2. NotificationsList - Dropdown showing unread notifications
 * 3. NotificationsCenter - Full page with all notifications
 * 4. NotificationItem - Individual notification card
 * 5. NotificationFilters - Filter by read/unread, event type, etc.
 */

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

// ============================================================================
// NOTIFICATION BELL COMPONENT
// ============================================================================

export const NotificationBell = ({ user }) => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  // Fetch unread count on mount and poll
  useEffect(() => {
    fetchUnreadCount();
    // Poll every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchUnreadCount = async () => {
    try {
      const response = await axios.get('/rspc/api/notifications/unread-count/', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/rspc/api/notifications/', {
        params: { 'read_status': 'unread', 'limit': 10 },
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setNotifications(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBellClick = () => {
    if (!showDropdown) {
      fetchNotifications();
    }
    setShowDropdown(!showDropdown);
  };

  return (
    <div ref={dropdownRef} className="notification-bell-container" style={{ position: 'relative', display: 'inline-block' }}>
      {/* Bell Icon Button */}
      <button
        className="notification-bell"
        onClick={handleBellClick}
        style={{
          background: 'none',
          border: 'none',
          fontSize: '24px',
          cursor: 'pointer',
          position: 'relative'
        }}
        title="Notifications"
      >
        🔔
        {unreadCount > 0 && (
          <span
            className="unread-badge"
            style={{
              position: 'absolute',
              top: '-5px',
              right: '-5px',
              backgroundColor: '#FF4444',
              color: 'white',
              borderRadius: '50%',
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: 'bold'
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <div
          className="notification-dropdown"
          style={{
            position: 'absolute',
            right: 0,
            top: '40px',
            backgroundColor: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            minWidth: '300px',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 1000
          }}
        >
          {loading && <div style={{ padding: '16px', textAlign: 'center' }}>Loading...</div>}

          {!loading && notifications.length === 0 && (
            <div style={{ padding: '16px', textAlign: 'center', color: '#999' }}>
              No new notifications
            </div>
          )}

          {!loading && notifications.map((notif) => (
            <NotificationItem key={notif.nid} notification={notif} compact={true} />
          ))}

          {!loading && notifications.length > 0 && (
            <div style={{ padding: '12px', borderTop: '1px solid #eee', textAlign: 'center' }}>
              <a
                href="/rspc/notifications/"
                style={{ color: '#0066cc', textDecoration: 'none', fontWeight: '500' }}
              >
                View All Notifications
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


// ============================================================================
// NOTIFICATION ITEM COMPONENT
// ============================================================================

export const NotificationItem = ({ notification, compact = false, onMarkRead, onDelete }) => {
  const [isRead, setIsRead] = useState(notification.is_read);

  const handleMarkRead = async () => {
    try {
      await axios.post(
        `/rspc/api/notifications/${notification.nid}/mark-read/`,
        { is_read: true },
        { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }
      );
      setIsRead(true);
      if (onMarkRead) onMarkRead(notification.nid);
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(
        `/rspc/api/notifications/${notification.nid}/`,
        { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }
      );
      if (onDelete) onDelete(notification.nid);
    } catch (error) {
      console.error('Error deleting notification:', error);
    }
  };

  const getEventTypeIcon = (eventType) => {
    const iconMap = {
      'expenditure_pending_approval': '⏳',
      'expenditure_approved': '✅',
      'expenditure_rejected': '❌',
      'budget_reallocated': '💰',
      'proposal_pending_verification': '📋',
      'proposal_approved': '🎉',
      'proposal_rejected': '🚫',
      'staff_committee_pending': '👥',
      'staff_hod_pending': '👔',
      'staff_rspc_pending': '🏛️',
      'staff_appointed': '👤',
      'fund_request_pending': '💵',
      'fund_approved': '💳',
      'patent_updated': '🔬'
    };
    return iconMap[eventType] || '📧';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const itemStyle = {
    padding: compact ? '12px' : '16px',
    borderBottom: '1px solid #eee',
    backgroundColor: isRead ? 'white' : '#f0f8ff',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    position: 'relative'
  };

  const titleStyle = {
    fontWeight: isRead ? '400' : '600',
    margin: '0 0 8px 0',
    color: '#333',
    fontSize: compact ? '14px' : '16px'
  };

  const messageStyle = {
    fontSize: compact ? '12px' : '14px',
    color: '#666',
    margin: '0 0 8px 0',
    lineHeight: '1.4',
    display: compact ? '-webkit-box' : 'block',
    WebkitLineClamp: compact ? 2 : undefined,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden'
  };

  return (
    <div style={itemStyle} className="notification-item">
      {/* Icon and Content */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <span style={{ fontSize: '24px' }}>
          {getEventTypeIcon(notification.event_type)}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h4 style={titleStyle}>{notification.title}</h4>
          <p style={messageStyle}>{notification.message}</p>
          <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
            {formatDate(notification.created_at)}
          </div>

          {/* Action Buttons */}
          {!compact && (
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              {!isRead && (
                <button
                  onClick={handleMarkRead}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#0066cc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Mark as Read
                </button>
              )}
              <button
                onClick={handleDelete}
                style={{
                  padding: '6px 12px',
                  fontSize: '12px',
                  backgroundColor: '#ccc',
                  color: '#333',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
              {notification.entity_id && (
                <a
                  href={`/rspc/${notification.entity_type}/${notification.entity_id}/`}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#f0f0f0',
                    color: '#0066cc',
                    border: '1px solid #0066cc',
                    borderRadius: '4px',
                    textDecoration: 'none',
                    cursor: 'pointer'
                  }}
                >
                  View Details
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


// ============================================================================
// NOTIFICATION FILTERS COMPONENT
// ============================================================================

export const NotificationFilters = ({ onFilterChange }) => {
  const [readStatus, setReadStatus] = useState('all');
  const [eventType, setEventType] = useState('');
  const [entityType, setEntityType] = useState('');

  const eventTypes = [
    { value: 'expenditure_pending_approval', label: 'Expenditure Pending' },
    { value: 'expenditure_approved', label: 'Expenditure Approved' },
    { value: 'expenditure_rejected', label: 'Expenditure Rejected' },
    { value: 'budget_reallocated', label: 'Budget Reallocated' },
    { value: 'proposal_pending_verification', label: 'Proposal Pending' },
    { value: 'proposal_approved', label: 'Proposal Approved' },
    { value: 'proposal_rejected', label: 'Proposal Rejected' },
    { value: 'staff_committee_pending', label: 'Staff Committee' },
    { value: 'staff_hod_pending', label: 'Staff HOD' },
    { value: 'staff_rspc_pending', label: 'Staff RSPC' },
    { value: 'staff_appointed', label: 'Staff Appointed' },
    { value: 'fund_request_pending', label: 'Fund Request' },
    { value: 'fund_approved', label: 'Fund Approved' },
    { value: 'patent_updated', label: 'Patent Updated' }
  ];

  const entityTypes = [
    { value: 'expenditure', label: 'Expenditure' },
    { value: 'project', label: 'Project' },
    { value: 'budget', label: 'Budget' },
    { value: 'staff', label: 'Staff' },
    { value: 'fund', label: 'Fund' },
    { value: 'patent', label: 'Patent' }
  ];

  const handleFilterChange = () => {
    onFilterChange({ readStatus, eventType, entityType });
  };

  useEffect(() => {
    handleFilterChange();
  }, [readStatus, eventType, entityType]);

  return (
    <div style={{ display: 'flex', gap: '16px', padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px', flexWrap: 'wrap' }}>
      {/* Read Status Filter */}
      <div>
        <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
          Status:
        </label>
        <select
          value={readStatus}
          onChange={(e) => setReadStatus(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          <option value="all">All</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
        </select>
      </div>

      {/* Event Type Filter */}
      <div>
        <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
          Event Type:
        </label>
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          <option value="">All Event Types</option>
          {eventTypes.map((et) => (
            <option key={et.value} value={et.value}>
              {et.label}
            </option>
          ))}
        </select>
      </div>

      {/* Entity Type Filter */}
      <div>
        <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
          Entity Type:
        </label>
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          <option value="">All Entity Types</option>
          {entityTypes.map((et) => (
            <option key={et.value} value={et.value}>
              {et.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};


// ============================================================================
// NOTIFICATIONS CENTER (FULL PAGE)
// ============================================================================

export const NotificationsCenter = ({ user }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filters, setFilters] = useState({
    readStatus: 'all',
    eventType: '',
    entityType: ''
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchNotifications();
  }, [filters, page]);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const params = {
        limit: 20,
        offset: (page - 1) * 20,
        read_status: filters.readStatus || 'all',
        event_type: filters.eventType || undefined,
        entity_type: filters.entityType || undefined
      };

      // Remove undefined values
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);

      const response = await axios.get('/rspc/api/notifications/', {
        params,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      setNotifications(response.data.results || response.data);
      setTotalPages(Math.ceil((response.data.count || 0) / 20));

      // Also fetch unread count
      const countResponse = await axios.get('/rspc/api/notifications/unread-count/', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setUnreadCount(countResponse.data.unread_count);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await axios.post(
        '/rspc/api/notifications/mark-all-read/',
        {},
        { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }
      );
      fetchNotifications();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  const handleNotificationDelete = (nid) => {
    setNotifications(notifications.filter((n) => n.nid !== nid));
    fetchNotifications();
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Notifications</h1>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            style={{
              padding: '8px 16px',
              backgroundColor: '#0066cc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Mark All as Read ({unreadCount})
          </button>
        )}
      </div>

      {/* Filters */}
      <NotificationFilters onFilterChange={setFilters} />

      {/* Notifications List */}
      <div style={{ marginTop: '20px' }}>
        {loading && <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>Loading notifications...</div>}

        {!loading && notifications.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
            No notifications to display
          </div>
        )}

        {!loading && notifications.map((notif) => (
          <NotificationItem
            key={notif.nid}
            notification={notif}
            compact={false}
            onDelete={() => handleNotificationDelete(notif.nid)}
          />
        ))}
      </div>

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '24px' }}>
          <button
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              backgroundColor: page === 1 ? '#f0f0f0' : 'white',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              borderRadius: '4px'
            }}
          >
            Previous
          </button>
          <span style={{ padding: '8px 16px' }}>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page === totalPages}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              backgroundColor: page === totalPages ? '#f0f0f0' : 'white',
              cursor: page === totalPages ? 'not-allowed' : 'pointer',
              borderRadius: '4px'
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationsCenter;
