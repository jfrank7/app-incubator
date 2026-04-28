import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import IdeaForm from './pages/IdeaForm'
import RunList from './pages/RunList'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IdeaForm />} />
        <Route path="/runs" element={<RunList />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
