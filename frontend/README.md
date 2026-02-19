# Agent Memory Frontend

Minimal frontend for visualizing Agent Brain projects and dependency graphs.

## Features

- **Project Dashboard**: View all analyzed projects with key metrics
- **Project Details**: Deep dive into project structure, components, and analytics
- **Dependency Graph**: Interactive visualization of code dependencies
- **Component Search**: Filter and search through project components
- **Technology Stack**: Visual representation of technologies used

## Tech Stack

- React 18 with TypeScript
- TailwindCSS for styling
- React Force Graph for dependency visualization
- Axios for API communication
- React Router for navigation

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:3000

## API Integration

The frontend connects to the Agent Brain API at `http://localhost:8000`. Make sure the backend is running before starting the frontend.

## Project Structure

```
src/
├── components/
│   ├── ProjectList.tsx      # Main project dashboard
│   ├── ProjectDetail.tsx    # Detailed project view
│   └── GraphVisualization.tsx # Dependency graph component
├── services/
│   └── api.ts               # API service layer
├── types/
│   └── index.ts             # TypeScript type definitions
├── App.tsx                  # Main application component
├── main.tsx                 # Application entry point
└── index.css                # Global styles
```

## Usage

1. **Project List**: View all analyzed projects with search functionality
2. **Project Details**: Click on any project to see detailed information
3. **Components Tab**: Browse and filter project components
4. **Graph Tab**: Interactive dependency graph visualization
5. **Overview Tab**: Project analytics and technology stack

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
