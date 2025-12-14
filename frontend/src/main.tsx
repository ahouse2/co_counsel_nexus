import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

import { HaloProvider } from './context/HaloContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <HaloProvider>
            <App />
        </HaloProvider>
    </React.StrictMode>,
)
