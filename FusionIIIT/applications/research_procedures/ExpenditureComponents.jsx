/**
 * RSPC Expenditure Approval System - Frontend Components
 * UC-012, UC-013, BR-RSPC-13 Implementation
 * 
 * Components:
 * 1. ExpenditureForm - Create expenditure requests
 * 2. ExpendituresList - List with role-based filtering
 * 3. ApprovalInterface - Approve/reject interface
 * 4. ExpenditureTimeline - Approval workflow progress
 * 5. ApprovalHistory - View all approval steps
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * ExpenditureForm Component
 * Create new expenditure request with validation
 */
export const ExpenditureForm = ({ projectId, onSuccess }) => {
  const [formData, setFormData] = useState({
    project_id: projectId,
    category: '',
    amount: '',
    purpose: '',
    supporting_documents: []
  });
  
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const categories = [
    'MANPOWER',
    'EQUIPMENT',
    'CONSUMABLES',
    'TRAVEL',
    'CONTINGENCY',
    'OVERHEAD',
    'OTHER'
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleFileUpload = (e) => {
    const files = e.target.files;
    setFormData(prev => ({
      ...prev,
      supporting_documents: [...prev.supporting_documents, ...Array.from(files)]
    }));
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.category) {
      newErrors.category = 'Category is required';
    }
    
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      newErrors.amount = 'Amount must be positive';
    }
    
    if (!formData.purpose || formData.purpose.length < 20) {
      newErrors.purpose = 'Purpose must be at least 20 characters';
    }
    
    if (parseFloat(formData.amount) > 50000 && formData.supporting_documents.length === 0) {
      newErrors.supporting_documents = 'Supporting documents required for amounts > ₹50,000';
    }
    
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    setLoading(true);
    setSuccessMessage('');
    
    try {
      const submitData = new FormData();
      submitData.append('project_id', formData.project_id);
      submitData.append('category', formData.category);
      submitData.append('amount', formData.amount);
      submitData.append('purpose', formData.purpose);
      
      formData.supporting_documents.forEach((doc, index) => {
        submitData.append(`supporting_documents_${index}`, doc);
      });
      
      const response = await axios.post('/api/rspc/expenditures/', submitData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setSuccessMessage(`Expenditure created successfully! ID: ${response.data.eid}`);
      setFormData({
        project_id: projectId,
        category: '',
        amount: '',
        purpose: '',
        supporting_documents: []
      });
      
      if (onSuccess) {
        onSuccess(response.data);
      }
    } catch (error) {
      setErrors({
        submit: error.response?.data?.error || 'Failed to create expenditure'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="expenditure-form">
      <h2>Create Expenditure Request</h2>
      
      {successMessage && (
        <div className="alert alert-success">{successMessage}</div>
      )}
      
      {errors.submit && (
        <div className="alert alert-error">{errors.submit}</div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="category">Category *</label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleInputChange}
            className={errors.category ? 'input-error' : ''}
          >
            <option value="">Select Category</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          {errors.category && <span className="error-text">{errors.category}</span>}
        </div>
        
        <div className="form-group">
          <label htmlFor="amount">Amount (₹) *</label>
          <input
            id="amount"
            type="number"
            name="amount"
            value={formData.amount}
            onChange={handleInputChange}
            placeholder="0"
            step="0.01"
            className={errors.amount ? 'input-error' : ''}
          />
          {errors.amount && <span className="error-text">{errors.amount}</span>}
        </div>
        
        <div className="form-group">
          <label htmlFor="purpose">Purpose of Expenditure *</label>
          <textarea
            id="purpose"
            name="purpose"
            value={formData.purpose}
            onChange={handleInputChange}
            placeholder="Detailed purpose (min 20 characters)"
            rows="4"
            className={errors.purpose ? 'input-error' : ''}
          />
          {errors.purpose && <span className="error-text">{errors.purpose}</span>}
        </div>
        
        {formData.amount && parseFloat(formData.amount) > 50000 && (
          <div className="form-group">
            <label htmlFor="documents">Supporting Documents (Required for > ₹50,000)</label>
            <input
              id="documents"
              type="file"
              multiple
              onChange={handleFileUpload}
              className={errors.supporting_documents ? 'input-error' : ''}
            />
            {errors.supporting_documents && (
              <span className="error-text">{errors.supporting_documents}</span>
            )}
          </div>
        )}
        
        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary"
        >
          {loading ? 'Creating...' : 'Create Request'}
        </button>
      </form>
    </div>
  );
};

/**
 * ExpendituresList Component
 * Display expenditures with role-based filtering
 */
export const ExpendituresList = ({ filters = {} }) => {
  const [expenditures, setExpenditures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });

  useEffect(() => {
    fetchExpenditures();
  }, [filters, pagination]);

  const fetchExpenditures = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      params.append('page', pagination.page);
      params.append('page_size', pagination.pageSize);
      
      const response = await axios.get(`/api/rspc/expenditures/?${params.toString()}`);
      setExpenditures(response.data.results);
      setPagination(prev => ({
        ...prev,
        totalPages: Math.ceil(response.data.count / pagination.pageSize)
      }));
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to fetch expenditures');
    } finally {
      setLoading(false);
    }
  };

  const getApprovalTierLabel = (amount) => {
    if (amount <= 50000) return 'Level 1 (PI)';
    if (amount <= 200000) return 'Level 2 (PI→HOD)';
    return 'Level 3 (PI→HOD→RSPC)';
  };

  const getStatusBadgeClass = (status) => {
    const statusMap = {
      'PENDING': 'badge-warning',
      'PI_APPROVED': 'badge-info',
      'HOD_APPROVED': 'badge-info',
      'RSPC_APPROVED': 'badge-info',
      'APPROVED': 'badge-success',
      'REJECTED': 'badge-error'
    };
    return statusMap[status] || 'badge-default';
  };

  if (loading) return <div>Loading expenditures...</div>;
  if (error) return <div className="alert alert-error">{error}</div>;

  return (
    <div className="expenditures-list">
      <h2>Expenditures</h2>
      
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Project</th>
            <th>Category</th>
            <th>Amount</th>
            <th>Approval Tier</th>
            <th>Status</th>
            <th>Current Approver</th>
            <th>Requested</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {expenditures.map(exp => (
            <tr key={exp.eid}>
              <td>{exp.eid}</td>
              <td>{exp.project_name}</td>
              <td>{exp.category}</td>
              <td>₹{parseFloat(exp.amount).toLocaleString()}</td>
              <td>{getApprovalTierLabel(exp.amount)}</td>
              <td>
                <span className={`badge ${getStatusBadgeClass(exp.status)}`}>
                  {exp.status}
                </span>
              </td>
              <td>{exp.current_approver || '—'}</td>
              <td>{new Date(exp.request_date).toLocaleDateString()}</td>
              <td>
                <a href={`/expenditures/${exp.eid}/`} className="btn btn-sm btn-primary">
                  View
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {expenditures.length === 0 && (
        <p className="text-center text-muted">No expenditures found</p>
      )}
      
      {pagination.totalPages > 1 && (
        <div className="pagination">
          {Array.from({ length: pagination.totalPages }, (_, i) => (
            <button
              key={i + 1}
              onClick={() => setPagination(prev => ({ ...prev, page: i + 1 }))}
              className={pagination.page === i + 1 ? 'active' : ''}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * ApprovalInterface Component
 * Approve or reject expenditures
 */
export const ApprovalInterface = ({ expenditureId, currentApprover, onComplete }) => {
  const [action, setAction] = useState('approve');
  const [comments, setComments] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expenditure, setExpenditure] = useState(null);

  useEffect(() => {
    fetchExpenditure();
  }, [expenditureId]);

  const fetchExpenditure = async () => {
    try {
      const response = await axios.get(`/api/rspc/expenditures/${expenditureId}/`);
      setExpenditure(response.data);
    } catch (error) {
      setError('Failed to fetch expenditure details');
    }
  };

  const handleApprove = async () => {
    if (!comments.trim()) {
      setError('Comments are required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `/api/rspc/expenditures/${expenditureId}/approve/`,
        {
          expenditure_id: expenditureId,
          approver_role: currentApprover,
          comments: comments
        }
      );

      if (onComplete) {
        onComplete(response.data.expenditure);
      }
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to approve expenditure');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!reason.trim() || reason.length < 10) {
      setError('Rejection reason required (minimum 10 characters)');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `/api/rspc/expenditures/${expenditureId}/reject/`,
        {
          expenditure_id: expenditureId,
          rejecter_role: currentApprover,
          reason: reason
        }
      );

      if (onComplete) {
        onComplete(response.data.expenditure);
      }
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to reject expenditure');
    } finally {
      setLoading(false);
    }
  };

  if (!expenditure) return <div>Loading expenditure details...</div>;

  return (
    <div className="approval-interface">
      <div className="expenditure-summary">
        <h3>Expenditure {expenditure.eid} - {expenditure.category}</h3>
        <p><strong>Amount:</strong> ₹{parseFloat(expenditure.amount).toLocaleString()}</p>
        <p><strong>Purpose:</strong> {expenditure.purpose}</p>
        <p><strong>Requested by:</strong> {expenditure.requested_by_name}</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="approval-actions">
        <div className="action-group">
          <h4>Approve</h4>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Approval comments..."
            rows="3"
          />
          <button
            onClick={handleApprove}
            disabled={loading}
            className="btn btn-success"
          >
            {loading ? 'Processing...' : 'Approve'}
          </button>
        </div>

        <div className="action-group">
          <h4>Reject</h4>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Rejection reason (minimum 10 characters)..."
            rows="3"
          />
          <button
            onClick={handleReject}
            disabled={loading}
            className="btn btn-danger"
          >
            {loading ? 'Processing...' : 'Reject'}
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * ExpenditureTimeline Component
 * Show approval workflow progress
 */
export const ExpenditureTimeline = ({ expenditure }) => {
  const getApprovalTier = (amount) => {
    if (amount <= 50000) return 1;
    if (amount <= 200000) return 2;
    return 3;
  };

  const tier = getApprovalTier(expenditure.amount);
  const stages = [
    { level: 1, role: 'PI', label: 'PI Approval' },
    { level: 2, role: 'HOD', label: 'HOD Approval', visible: tier >= 2 },
    { level: 3, role: 'RSPC', label: 'RSPC Admin Approval', visible: tier >= 3 }
  ];

  const getStageStatus = (level) => {
    const stageMap = {
      'PENDING': level === 1 ? 'pending' : 'waiting',
      'PI_APPROVED': level <= 1 ? 'completed' : (level === 2 ? 'pending' : 'waiting'),
      'HOD_APPROVED': level <= 2 ? 'completed' : 'pending',
      'RSPC_APPROVED': 'completed',
      'APPROVED': 'completed',
      'REJECTED': 'rejected'
    };

    return stageMap[expenditure.status] || 'waiting';
  };

  return (
    <div className="expenditure-timeline">
      <h3>Approval Workflow</h3>
      
      <div className="timeline">
        {stages.filter(s => s.visible !== false).map((stage, index) => (
          <div
            key={stage.level}
            className={`timeline-stage stage-${getStageStatus(stage.level)}`}
          >
            <div className="stage-number">{stage.level}</div>
            <div className="stage-content">
              <h4>{stage.label}</h4>
              <p className="stage-role">{stage.role}</p>
              <p className="stage-status">{getStageStatus(stage.level)}</p>
            </div>
            {index < stages.filter(s => s.visible !== false).length - 1 && (
              <div className="timeline-arrow">→</div>
            )}
          </div>
        ))}
      </div>

      {expenditure.status === 'APPROVED' && (
        <div className="alert alert-success">
          ✓ Fully Approved
        </div>
      )}

      {expenditure.status === 'REJECTED' && (
        <div className="alert alert-error">
          ✗ Rejected - Please revise and resubmit
        </div>
      )}
    </div>
  );
};

/**
 * ApprovalHistory Component
 * View all approval steps
 */
export const ApprovalHistory = ({ expenditureId }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchHistory();
  }, [expenditureId]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/rspc/expenditures/${expenditureId}/history/`);
      setHistory(response.data.history);
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to fetch approval history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading history...</div>;
  if (error) return <div className="alert alert-error">{error}</div>;
  if (history.length === 0) return <div>No approval history available</div>;

  return (
    <div className="approval-history">
      <h3>Approval History</h3>
      
      <table className="table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Approver</th>
            <th>Action</th>
            <th>Comments</th>
            <th>Date & Time</th>
          </tr>
        </thead>
        <tbody>
          {history.map((record, index) => (
            <tr key={index}>
              <td><strong>{record.approver_role}</strong></td>
              <td>{record.approver_name}</td>
              <td>
                <span className={`badge badge-${record.action === 'APPROVED' ? 'success' : 'error'}`}>
                  {record.action}
                </span>
              </td>
              <td>{record.comments || '—'}</td>
              <td>{new Date(record.approved_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
