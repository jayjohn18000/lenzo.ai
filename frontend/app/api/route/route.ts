export async function POST(req: Request) {
  const body = await req.json();
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  const r = await fetch(`${backend}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await r.json();
  return new Response(JSON.stringify(data), {
    status: r.status,
    headers: { "Content-Type": "application/json" },
  });
}
