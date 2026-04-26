import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './layout/AppShell'
import OverviewPage from './pages/OverviewPage'
import DemographicsPage from './pages/DemographicsPage'
import RegionsPage from './pages/RegionsPage'
import PersonasPage from './pages/PersonasPage'
import PopulationPage from './pages/OntologyPage'
import RegionComparePage from './pages/RegionComparePage'
import ResultsPage from './pages/ResultsPage'
import OntologyPage from './pages/KGPage'
import OperationsPage from './pages/OperationsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="ontology" element={<OntologyPage />} />
        <Route path="kg" element={<Navigate to="/ontology" replace />} />
        <Route path="operations" element={<OperationsPage />} />
        <Route path="demographics" element={<DemographicsPage />} />
        <Route path="regions" element={<RegionsPage />} />
        <Route path="regions/compare" element={<RegionComparePage />} />
        <Route path="personas" element={<PersonasPage />} />
        <Route path="population" element={<PopulationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
