import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/base.css'
import './styles/app.css'
import App from './App.jsx'
import { RouterProvider } from './lib/router'
import { SessionProvider } from './lib/session'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider>
      <SessionProvider>
        <App />
      </SessionProvider>
    </RouterProvider>
  </StrictMode>,
)
