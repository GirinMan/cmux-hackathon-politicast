import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import BoardPage from './pages/BoardPage';
import BoardTopicDetail from './pages/BoardTopicDetail';
import KgViewerPage from './pages/KgViewerPage';
import PersonasPage from './pages/PersonasPage';
import PollTrajectoryPage from './pages/PollTrajectoryPage';
import PredictionTrajectoryPage from './pages/PredictionTrajectoryPage';
import ScenarioBranchPage from './pages/ScenarioBranchPage';
import ScenarioTreePage from './pages/ScenarioTreePage';
import SetupPage from './pages/SetupPage';
import AdminDashboardPage from './pages/admin/AdminDashboardPage';
import DataSourcesPage from './pages/admin/DataSourcesPage';
import LoginPage from './pages/admin/LoginPage';
import ModerationPage from './pages/admin/ModerationPage';
import SimRunsPage from './pages/admin/SimRunsPage';
import UnresolvedEntitiesPage from './pages/admin/UnresolvedEntitiesPage';

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route element={<Layout />}>
        <Route path="/" element={<SetupPage />} />
        <Route path="/personas" element={<PersonasPage />} />
        <Route path="/polls" element={<PollTrajectoryPage />} />
        <Route path="/prediction" element={<PredictionTrajectoryPage />} />
        <Route path="/scenarios" element={<ScenarioBranchPage />} />
        <Route path="/scenario-tree" element={<ScenarioTreePage />} />
        <Route path="/kg" element={<KgViewerPage />} />
        <Route path="/board" element={<BoardPage />} />
        <Route path="/board/topics/:id" element={<BoardTopicDetail />} />
      </Route>

      {/* Admin */}
      <Route path="/admin/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout admin />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/sim-runs" element={<SimRunsPage />} />
          <Route path="/admin/data-sources" element={<DataSourcesPage />} />
          <Route path="/admin/unresolved" element={<UnresolvedEntitiesPage />} />
          <Route path="/admin/moderation" element={<ModerationPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
