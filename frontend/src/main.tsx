import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// CSS 파일들을 직접 import
import './index.css'
import './styles/common.css'
import './styles/App.css'
import './styles/Header.css'
import './styles/TripPlanner.css'
import './styles/TripResult.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
