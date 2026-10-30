import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT Bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('fdrsetu_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle session expiration
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // If unauthorized and not already on login
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('fdrsetu_token');
        localStorage.removeItem('fdrsetu_user');
      }
    }
    return Promise.reject(error);
  }
);

export const systemService = {
  getHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
  getRoot: async () => {
    const response = await axios.get(API_BASE_URL.replace('/api/v1', '') || 'http://localhost:8000');
    return response.data;
  }
};

export const authService = {
  login: async (usernameOrEmail, password) => {
    const response = await apiClient.post('/auth/login', {
      username_or_email: usernameOrEmail,
      password: password,
    });
    return response.data;
  },
  registerInstitution: async (data) => {
    const response = await apiClient.post('/auth/register', data);
    return response.data;
  },
  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      localStorage.removeItem('fdrsetu_token');
      localStorage.removeItem('fdrsetu_user');
    }
  },
  getDemoAccounts: async () => {
    const response = await apiClient.get('/auth/demo-accounts');
    return response.data;
  }
};

export const institutionService = {
  getAll: async (params = {}) => {
    const response = await apiClient.get('/institutions', { params });
    return response.data;
  },
  getById: async (id) => {
    const response = await apiClient.get(`/institutions/${id}`);
    return response.data;
  },
  create: async (data) => {
    const response = await apiClient.post('/institutions', data);
    return response.data;
  },
  update: async (id, data) => {
    const response = await apiClient.patch(`/institutions/${id}`, data);
    return response.data;
  }
};

export const fdrService = {
  getAll: async (params = {}) => {
    const response = await apiClient.get('/fdr', { params });
    return response.data;
  },
  getStatistics: async (params = {}) => {
    const response = await apiClient.get('/fdr/statistics', { params });
    return response.data;
  },
  getById: async (id) => {
    const response = await apiClient.get(`/fdr/${id}`);
    return response.data;
  },
  create: async (fdrData) => {
    const response = await apiClient.post('/fdr', fdrData);
    return response.data;
  },
  update: async (id, fdrData) => {
    const response = await apiClient.patch(`/fdr/${id}`, fdrData);
    return response.data;
  },
  delete: async (id) => {
    const response = await apiClient.delete(`/fdr/${id}`);
    return response.data;
  },
  submitForScrutiny: async (id) => {
    const response = await apiClient.post(`/fdr/${id}/submit`);
    return response.data;
  },
  uploadDocument: async (fdrId, file, documentType = "FDR_INSTRUMENT") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    const response = await apiClient.post(`/fdr/${fdrId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  deleteDocument: async (docId) => {
    const response = await apiClient.delete(`/documents/${docId}`);
    return response.data;
  }
};

export const documentService = {
  getDownloadUrl: (docId) => `${API_BASE_URL}/documents/${docId}/download`,
  getPreviewUrl: (docId) => `${API_BASE_URL}/documents/${docId}/preview`,
  downloadWithAuth: async (docId, filename) => {
    const response = await apiClient.get(`/documents/${docId}/download`, {
      responseType: 'blob'
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `fdr_document_${docId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
  },
  getPreviewBlob: async (docId) => {
    const response = await apiClient.get(`/documents/${docId}/preview`, {
      responseType: 'blob'
    });
    return {
      blobUrl: window.URL.createObjectURL(new Blob([response.data], { type: response.headers['content-type'] })),
      mimeType: response.headers['content-type']
    };
  }
};

export const ocrService = {
  extract: async (fdrId) => {
    const response = await apiClient.post(`/fdr/${fdrId}/extract`);
    return response.data;
  },
  getExtraction: async (fdrId) => {
    const response = await apiClient.get(`/fdr/${fdrId}/extraction`);
    return response.data;
  },
  reviewAndCorrect: async (fdrId, correctedFields) => {
    const response = await apiClient.patch(`/fdr/${fdrId}/extraction`, {
      corrected_fields: correctedFields
    });
    return response.data;
  }
};

export const verificationService = {
  verify: async (fdrId) => {
    const response = await apiClient.post(`/fdr/${fdrId}/verify`);
    return response.data;
  },
  getReport: async (fdrId) => {
    const response = await apiClient.get(`/fdr/${fdrId}/verification-report`);
    return response.data;
  },
  getDiscrepancies: async (fdrId, status) => {
    const response = await apiClient.get(`/fdr/${fdrId}/discrepancies`, {
      params: { status }
    });
    return response.data;
  },
  raiseDiscrepancy: async (fdrId, data) => {
    const response = await apiClient.post(`/fdr/${fdrId}/discrepancies`, data);
    return response.data;
  },
  respondToDiscrepancy: async (discId, responseText) => {
    const response = await apiClient.post(`/discrepancies/${discId}/respond`, {
      response_text: responseText
    });
    return response.data;
  },
  resolveDiscrepancy: async (discId, resolutionNote, newStatus = 'RESOLVED') => {
    const response = await apiClient.post(`/discrepancies/${discId}/resolve`, {
      resolution_note: resolutionNote,
      status: newStatus
    });
    return response.data;
  },
  submitScrutinyRecommendation: async (fdrId, recommendation, remarks) => {
    const response = await apiClient.post(`/fdr/${fdrId}/scrutiny-recommendation`, {
      recommendation,
      remarks
    });
    return response.data;
  },
  getRules: async () => {
    const response = await apiClient.get('/verification/rules');
    return response.data;
  },
  updateRule: async (ruleId, data) => {
    const response = await apiClient.patch(`/verification/rules/${ruleId}`, data);
    return response.data;
  }
};

export default apiClient;
