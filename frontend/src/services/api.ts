import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
    // In development (Vite), this is proxied to http://localhost:8000
    // In production (Nginx), this is proxied to the backend service
    baseURL: '/',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

export const endpoints = {
    // Graph
    graph: {
        neighbors: (nodeId: string) => api.get(`/api/graph/neighbors/${nodeId}`),
        query: (cypher: string) => api.post('/api/graph/query', { query: cypher }),
    },
    // Chat / Agents
    agents: {
        list: () => api.get('/agents/'),
        chat: (message: string) => api.post('/agents/chat', { message }),
    },
    // Documents
    documents: {
        list: (caseId: string) => api.get(`/api/documents/${caseId}/documents`),
        upload: (caseId: string, formData: FormData, relativePath?: string, apiKeys?: { gemini?: string, courtListener?: string }) => {
            let url = `/api/documents/upload?case_id=${caseId}&doc_type=my_documents`;
            if (relativePath) {
                url += `&relative_path=${encodeURIComponent(relativePath)}`;
            }
            const headers: any = { 'Content-Type': 'multipart/form-data' };
            if (apiKeys?.gemini) headers['x-gemini-api-key'] = apiKeys.gemini;
            if (apiKeys?.courtListener) headers['x-courtlistener-api-key'] = apiKeys.courtListener;

            return api.post(url, formData, { headers });
        },
        uploadDirectory: (caseId: string, formData: FormData) => {
            return api.post(`/api/documents/upload_directory?case_id=${caseId}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
        },
    },
    // Timeline
    timeline: {
        get: (caseId: string) => api.get(`/timeline/${caseId}`),
        list: (page = 1, pageSize = 10) => api.get(`/timeline?page=${page}&page_size=${pageSize}`),
        generate: (prompt: string, caseId: string) => api.post('/timeline/generate', { prompt, case_id: caseId }),
    },
    // Context
    context: {
        query: (q: string) => api.post('/query', { query: q }),
    },
    // Halo
    halo: {
        bootstrap: () => api.get('/api/halo/bootstrap'),
    },
};

export default api;
