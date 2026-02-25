import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ProfilePage from './pages/ProfilePage'
import JobSearchPage from './pages/JobSearchPage'
import ApplicationsPage from './pages/ApplicationsPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/search" element={<JobSearchPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
      </Routes>
    </Layout>
  )
}

export default App
