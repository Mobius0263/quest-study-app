import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthProvider.jsx'
import ScrollToTop from './components/layout/ScrollToTop.jsx'
import AppShell from './components/layout/AppShell.jsx'
import ProtectedRoute from './routes/ProtectedRoute.jsx'
import RoleGate from './routes/RoleGate.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import QuestBoardPage from './pages/QuestBoardPage.jsx'
import QuestDetailPage from './pages/QuestDetailPage.jsx'
import QuestQuizPage from './pages/QuestQuizPage.jsx'
import BossFightPage from './pages/BossFightPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import TeacherPage from './pages/TeacherPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ScrollToTop />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="quests" element={<QuestBoardPage />} />
              <Route path="quests/:questId" element={<QuestDetailPage />} />
              <Route path="quests/:questId/quiz" element={<QuestQuizPage />} />
              <Route
                path="boss/:quizId"
                element={
                  <RoleGate role="student">
                    <BossFightPage />
                  </RoleGate>
                }
              />
              <Route path="profile" element={<ProfilePage />} />
              <Route
                path="teacher"
                element={
                  <RoleGate role="teacher">
                    <TeacherPage />
                  </RoleGate>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
