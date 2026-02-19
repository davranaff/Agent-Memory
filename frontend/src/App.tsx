import { BrowserRouter as Router, NavLink, Route, Routes } from 'react-router-dom';
import ProjectList from './components/ProjectList';
import ProjectDetail from './components/ProjectDetail';
import ApiExplorer from './components/ApiExplorer';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <h1 className="text-lg font-semibold text-gray-900">Agent Memory</h1>
            <nav className="flex items-center gap-4 text-sm">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  isActive ? 'font-medium text-blue-700' : 'text-gray-600 hover:text-gray-900'
                }
              >
                Projects
              </NavLink>
              <NavLink
                to="/api-explorer"
                className={({ isActive }) =>
                  isActive ? 'font-medium text-blue-700' : 'text-gray-600 hover:text-gray-900'
                }
              >
                API Explorer
              </NavLink>
            </nav>
          </div>
        </header>
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/project/:id" element={<ProjectDetail />} />
          <Route path="/api-explorer" element={<ApiExplorer />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
