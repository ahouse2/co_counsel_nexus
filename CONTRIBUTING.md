# Local Development Guide

## Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional, for database services)

## Backend Setup

1.  **Navigate to backend directory**:
    ```bash
    cd backend
    ```

2.  **Create virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables**:
    Create a `.env` file in the `backend` directory. You can copy `.env.example` if it exists, or use the following defaults:
    ```env
    GEMINI_API_KEY=your_key_here
    COURTLISTENER_API_KEY=your_key_here
    # ... other settings from config.py
    ```

5.  **Run the Server**:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    The API will be available at `http://localhost:8000`.

## Frontend Setup

1.  **Navigate to frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Run the Development Server**:
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:8088` (or similar, check console output).

## Running Databases (Optional but Recommended)
If you don't want to run the full Docker stack, you at least need the databases.
```bash
docker compose up -d qdrant neo4j
```
