import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    return (_jsxs(Routes, { children: [_jsxs(Route, { element: _jsx(Layout, {}), children: [_jsx(Route, { path: "/", element: _jsx(SetupPage, {}) }), _jsx(Route, { path: "/personas", element: _jsx(PersonasPage, {}) }), _jsx(Route, { path: "/polls", element: _jsx(PollTrajectoryPage, {}) }), _jsx(Route, { path: "/prediction", element: _jsx(PredictionTrajectoryPage, {}) }), _jsx(Route, { path: "/scenarios", element: _jsx(ScenarioBranchPage, {}) }), _jsx(Route, { path: "/scenario-tree", element: _jsx(ScenarioTreePage, {}) }), _jsx(Route, { path: "/kg", element: _jsx(KgViewerPage, {}) }), _jsx(Route, { path: "/board", element: _jsx(BoardPage, {}) }), _jsx(Route, { path: "/board/topics/:id", element: _jsx(BoardTopicDetail, {}) })] }), _jsx(Route, { path: "/admin/login", element: _jsx(LoginPage, {}) }), _jsx(Route, { element: _jsx(ProtectedRoute, {}), children: _jsxs(Route, { element: _jsx(Layout, { admin: true }), children: [_jsx(Route, { path: "/admin", element: _jsx(AdminDashboardPage, {}) }), _jsx(Route, { path: "/admin/sim-runs", element: _jsx(SimRunsPage, {}) }), _jsx(Route, { path: "/admin/data-sources", element: _jsx(DataSourcesPage, {}) }), _jsx(Route, { path: "/admin/unresolved", element: _jsx(UnresolvedEntitiesPage, {}) }), _jsx(Route, { path: "/admin/moderation", element: _jsx(ModerationPage, {}) })] }) }), _jsx(Route, { path: "*", element: _jsx(Navigate, { to: "/", replace: true }) })] }));
}
