# NextAGI Frontend

This is the Next.js frontend for NextAGI - an advanced AI reliability platform that detects and prevents hallucinations in LLM outputs.

## Environment Configuration

Before running the frontend, create a `.env.local` file in the frontend directory with the following variables:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=nextagi_test-key-123

# Development Settings
NODE_ENV=development
```

### Required Environment Variables

- `NEXT_PUBLIC_API_URL`: The backend API URL (defaults to http://localhost:8000)
- `NEXT_PUBLIC_BACKEND_URL`: Alternative backend URL (optional, falls back to NEXT_PUBLIC_API_URL)
- `NEXT_PUBLIC_API_KEY`: API key for authentication (defaults to nextagi_test-key-123 for development)

## Getting Started

First, ensure the backend is running on port 8000, then run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
