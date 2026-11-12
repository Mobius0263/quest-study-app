# Quest Study — Frontend

React + Vite frontend for Quest Study, built from the Duolingo-style UI guide in
`docs/reference`.

## Run

```bash
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies `/api` to the Django
backend on `http://localhost:8000`.

## Environment

Copy `.env.example` to `.env` if the API lives somewhere else:

```bash
VITE_API_URL=/api
```

The frontend talks to the REST API only. It never calls PostgreSQL or Ollama
directly.

## Scripts

- `npm run dev` — start the Vite dev server
- `npm run build` — production build
- `npm run lint` — run Oxlint
- `npm run preview` — preview the production build

## Batch status

- Batch 1 — foundation: routing, auth, API client, app shell, shared components,
  sprites/icons, loading/empty/error states, placeholder screens.
- Batch 2 — dashboard path.
- Batch 3 — quest board and Revision Quest CRUD.
- Batch 4 — quest detail and the regular quest quiz.
- Batch 5 — boss fight.
- Batch 6 — profile and streak calendar.
- Batch 7 — teacher view, integration and QA.
