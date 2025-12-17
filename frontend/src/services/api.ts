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
        agentQuery: (query: string, caseId: string = 'default_case') => api.post('/api/graph/agent', { query, case_id: caseId }),
    },
    // Chat / Agents
    agents: {
        list: () => api.get('/agents/'),
        chat: (message: string) => api.post('/agents/chat', { message }),
        run: (task: string, caseId: string) => api.post('/api/agents/run', { task, case_id: caseId }),
    },
    // Documents
    documents: {
        list: (caseId: string) => api.get(`/api/documents/${caseId}/documents`, {
            timeout: 0 // No timeout - allows unlimited time for heavy processing
        }),
        search: (query: string, topK: number = 10) => api.get('/api/documents/search', {
            params: { query, top_k: topK }
        }),
        batchDelete: (docIds: string[], caseId: string = 'default_case') =>
            api.post('/api/documents/batch/delete', { doc_ids: docIds }, { params: { case_id: caseId } }),
        batchReprocess: (docIds: string[], caseId: string = 'default_case') =>
            api.post('/api/documents/batch/reprocess', { doc_ids: docIds }, { params: { case_id: caseId } }),
        batchDownload: (docIds: string[], caseId: string = 'default_case') =>
            api.post('/api/documents/batch/download', { doc_ids: docIds }, {
                params: { case_id: caseId },
                responseType: 'blob'
            }),
        getGraph: (caseId: string, docId: string, hops: number = 1) =>
            api.get(`/api/documents/${caseId}/documents/${docId}/graph`, { params: { hops } }),
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
        uploadChunk: (caseId: string, formData: FormData, onUploadProgress?: (progressEvent: any) => void) => {
            return api.post(`/api/documents/upload_chunk?case_id=${caseId}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                timeout: 3600000, // 1 hour for large chunks
                onUploadProgress
            });
        },
        pendingReview: (caseId: string) => api.get(`/api/documents/pending_review?case_id=${caseId}`),
        approveClassification: (docId: string) => api.post(`/api/documents/${docId}/approve`),
        updateMetadata: (docId: string, metadata: any) => api.post(`/api/documents/${docId}/update_metadata`, metadata),
        getEntities: (docId: string) => api.get(`/api/documents/${docId}/entities`),
        getOCR: (docId: string) => api.get(`/api/documents/${docId}/ocr`),
        triggerOCR: (docId: string) => api.post(`/api/documents/${docId}/ocr`),
        getClustering: (limit: number = 1000) => api.get('/api/documents/clustering', { params: { limit } }),
        triggerLocalIngestion: (caseId: string, directoryPath: string = ".") => {
            const formData = new FormData();
            formData.append('case_id', caseId);
            formData.append('directory_path', directoryPath);
            return api.post('/api/documents/ingestion/local', formData);
        },
    },
    // Timeline
    timeline: {
        get: (caseId: string) => api.get(`/api/timeline/${caseId}`),
        list: (page = 1, pageSize = 10) => api.get(`/api/timeline?page=${page}&page_size=${pageSize}`),
        generate: (prompt: string, caseId: string) => api.post('/api/timeline/generate', { prompt, case_id: caseId }),
        narrative: {
            generate: (caseId: string) => api.get(`/api/narrative/${caseId}/generate`),
            contradictions: (caseId: string) => api.get(`/api/narrative/${caseId}/contradictions`),
            branching: (caseId: string, pivot: string, fact: string) => api.post(`/api/narrative/${caseId}/branching`, { pivot_point: pivot, alternative_fact: fact }),
            storyArc: (caseId: string) => api.get(`/api/narrative/${caseId}/story_arc`),
        },
    },
    // Context
    context: {
        query: (query: string, caseId: string) => api.post('/api/context/query', { query, case_id: caseId }),
    },
    // Halo
    halo: {
        bootstrap: () => api.get('/api/halo/bootstrap'),
    },
    // Forensics
    forensics: {
        getMetadata: (docId: string) => api.get(`/api/forensics/${docId}`),
        getHexView: (docId: string) => api.get(`/api/forensics/${docId}/hex`),
        analyze: (docId: string, caseId: string) => api.post(`/api/forensics/${docId}/analyze?case_id=${caseId}`),
    },
    // Legal Theory
    legalTheory: {
        suggestions: (caseId: string) => api.get(`/api/legal_theory/suggestions?case_id=${caseId}`),
        subgraph: (cause: string) => api.get(`/api/legal_theory/${cause}/subgraph`),
        matchPrecedents: (facts: string) => api.post('/api/legal_theory/match_precedents', { case_facts: facts }),
        juryResonance: (argument: string, demographics: any) => api.post('/api/legal_theory/jury_resonance', { argument, jury_demographics: demographics }),
    },
    // Simulation
    simulation: {
        mootCourt: (data: any) => api.post('/api/simulation/moot_court', data),
        chatWithJuror: (data: any) => api.post('/api/simulation/juror_chat', data),
    },
    // Jury
    jury: {
        analyze: (text: string) => api.post('/api/jury-sentiment/analyze-argument', { text }),
        simulate: (argument: string, juryProfile: any) => api.post('/api/jury-sentiment/simulate-jury', { argument, jury_profile: juryProfile }),
        simulateIndividuals: (argument: string, jurors: any[]) => api.post('/api/jury-sentiment/simulate-individuals', { argument, jurors }),
        scoreCredibility: (witnessId: string, testimony: string) => api.post('/api/jury-sentiment/score-credibility', { witness_id: witnessId, testimony }),
    },
    // Financial Forensics
    financial: {
        traceCrypto: (address: string, chain: string) => api.post('/api/financial/crypto/trace', { address, chain }),
        scanAssets: (caseId: string) => api.post(`/api/financial/assets/scan/${caseId}`),
    },
    // Evidence Map
    evidenceMap: {
        analyze: (caseId: string) => api.post(`/api/evidence-map/analyze/${caseId}`),
    },
    // Jury Sentiment
    jurySentiment: {
        analyzeArgument: (data: any) => api.post('/api/jury-sentiment/analyze-argument', data),
        simulateJury: (data: any) => api.post('/api/jury-sentiment/simulate-jury', data),
        getReport: (caseId: string) => api.get(`/api/jury-sentiment/${caseId}/report`),
    },
    // Adversarial
    adversarial: {
        challenge: (caseId: string, theory: string) => api.post(`/api/adversarial/${caseId}/challenge`, { theory }),
    },
    // Devil's Advocate
    devilsAdvocate: {
        review: (caseId: string, caseTheory: string = "") => api.post(`/api/devils-advocate/${caseId}/review`, { case_theory: caseTheory }),
        crossExamine: (statement: string, profile: string = "") => api.post('/api/devils-advocate/cross-examine', { witness_statement: statement, witness_profile: profile }),
        motionToDismiss: (caseId: string, grounds: string[]) => api.post(`/api/devils-advocate/${caseId}/motion_to_dismiss`, { grounds }),
    },
    // Document Drafting
    drafting: {
        autocomplete: (currentText: string, cursorPosition: number, context: string = "") => api.post('/api/drafting/autocomplete', { current_text: currentText, cursor_position: cursorPosition, context }),
        toneCheck: (text: string, targetTone: string) => api.post('/api/drafting/tone-check', { text, target_tone: targetTone }),
    },
    // Case Management
    cases: {
        list: (skip = 0, limit = 100) => api.get(`/api/cases/?skip=${skip}&limit=${limit}`),
        create: (data: { name: string; description?: string }) => api.post('/api/cases/', data),
        get: (caseId: string) => api.get(`/api/cases/${caseId}`),
        update: (caseId: string, data: { name?: string; description?: string }) => api.put(`/api/cases/${caseId}`, data),
        delete: (caseId: string) => api.delete(`/api/cases/${caseId}`),
        export: (caseId: string) => api.get(`/api/cases/${caseId}/export`, { responseType: 'blob' }),
        import: (file: File) => {
            const formData = new FormData();
            formData.append('file', file);
            return api.post('/api/cases/import', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        },
        getCurrent: () => api.get('/api/cases/current'),
        setCurrent: (caseId: string) => api.post(`/api/cases/current?case_id=${caseId}`),
    },
    // Ingestion
    ingestion: {
        ingestLocal: (data: { source_path: string; document_id: string; recursive?: boolean; sync?: boolean }) => {
            const formData = new FormData();
            formData.append('source_path', data.source_path);
            formData.append('document_id', data.document_id);
            if (data.recursive !== undefined) formData.append('recursive', String(data.recursive));
            if (data.sync !== undefined) formData.append('sync', String(data.sync));
            return api.post('/api/ingestion/ingest_local_path', formData, {
                headers: { 'Content-Type': 'multipart/form-data' } // Although it's form data, the endpoint expects Form(...) params
            });
        }
    },
    // Research
    research: {
        // CourtListener
        addMonitor: (data: any) => api.post('/api/autonomous-courtlistener/monitors', data),
        listMonitors: () => api.get('/api/autonomous-courtlistener/monitors'),
        removeMonitor: (id: string) => api.delete(`/api/autonomous-courtlistener/monitors/${id}`),
        executeMonitor: (id: string) => api.post(`/api/autonomous-courtlistener/monitors/${id}/execute`),

        // Scraper
        addTrigger: (data: any) => api.post('/api/autonomous-scraping/triggers', data),
        listTriggers: () => api.get('/api/autonomous-scraping/triggers'),
        removeTrigger: (id: string) => api.delete(`/api/autonomous-scraping/triggers/${id}`),
        executeTrigger: (id: string) => api.post(`/api/autonomous-scraping/triggers/${id}/execute`),
        manualScrape: (source: string, query: string) => api.post('/api/autonomous-scraping/scrape', null, { params: { source, query } }),

        // Advanced Research
        shepardizeCase: (citation: string) => api.post('/api/shepardize', { citation }),
        profileJudge: (judgeName: string, jurisdiction: string) => api.post('/api/judge-profile', { judge_name: judgeName, jurisdiction }),
    },
    // Voice
    voice: {
        listPersonas: () => api.get('/api/voice/personas'),
        createSession: (caseId: string, personaId: string) => api.post('/api/voice/sessions', { case_id: caseId, persona_id: personaId }),
        processTurn: (sessionId: string, audioBlob: Blob) => {
            const formData = new FormData();
            formData.append('audio', audioBlob);
            return api.post(`/api/voice/sessions/${sessionId}/turn`, formData, {
                responseType: 'blob',
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        },
        getSession: (sessionId: string) => api.get(`/api/voice/sessions/${sessionId}`),
    },
    // Service of Process
    serviceOfProcess: {
        list: () => api.get('/api/service-of-process'),
        create: (documentId: string, recipientId: string) => api.post('/api/service-of-process', { document_id: documentId, recipient_id: recipientId }),
        listRecipients: () => api.get('/api/recipients'),
        createRecipient: (name: string, address: string) => api.post('/api/recipients', { name, address }),
        listDocuments: () => api.get('/api/documents'),
    },
    // Settings
    settings: {
        get: () => api.get('/api/settings'),
        update: (data: any) => api.put('/api/settings', data),
        models: () => api.get('/api/settings/models'),
    }
};

export default api;
