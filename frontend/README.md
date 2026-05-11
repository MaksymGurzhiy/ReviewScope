# Review Analysis System - Frontend

Modern React frontend for the Review Analysis System.

## Tech Stack

- React 18
- Vite (build tool)
- Tailwind CSS (styling)
- Recharts (charts and visualizations)
- Axios (API calls)
- React Dropzone (file upload)
- Lucide React (icons)

## Development

Install dependencies:
```bash
npm install
```

Run development server:
```bash
npm run dev
```

Frontend will be available at: http://localhost:3000

## Build for Production

```bash
npm run build
```

Built files will be in `dist/` directory.

## Features

- Drag & drop file upload
- Real-time analysis progress
- Interactive sentiment charts
- Topic visualization
- Keyword clouds
- Insights and recommendations
- Responsive design
- Modern UI/UX

## API Integration

Frontend connects to FastAPI backend at `http://localhost:8000`

Endpoints used:
- POST `/api/upload` - Upload review files
- POST `/api/analyze/{file_id}` - Run ML analysis
- GET `/api/health` - Backend health check
