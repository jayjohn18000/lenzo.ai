// frontend/app/api/route/route.ts - CORRECTED VERSION
export async function POST(req: Request) {
  const body = await req.json();
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  
  // Use development endpoint for testing (no auth required)
  const endpoint = process.env.NODE_ENV === 'development' ? "/dev/query" : "/api/v1/query";
  
  // Transform the request to match the simplified API
  const transformedBody = {
    prompt: body.prompt || "Test question",
    mode: "balanced", // speed, balanced, quality
    max_models: 3
  };
  
  console.log(`🔗 Calling: ${backend}${endpoint}`);
  console.log('📦 Request body:', JSON.stringify(transformedBody, null, 2));

  try {
    const r = await fetch(`${backend}${endpoint}`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        // NOTE: This will still fail due to missing API key
        // We need to add development bypass
      },
      body: JSON.stringify(transformedBody),
    });

    console.log(`📡 Response status: ${r.status}`);
    
    if (!r.ok) {
      const errorText = await r.text();
      console.error('❌ Backend error:', errorText);
      
      // If 403, it's likely auth issue
      if (r.status === 403) {
        throw new Error(`Authentication required - Status ${r.status}. Need to add API key or dev mode.`);
      }
      
      throw new Error(`Backend error: ${r.status} - ${errorText}`);
    }

    const data = await r.json();
    console.log('✅ Success response:', data);
    
    // Transform response to match frontend expectations
    const transformedResponse = {
      prompt: data.answer || transformedBody.prompt,
      responses: [{ model: data.winner_model, response: data.answer }],
      ranking: [{
        model: data.winner_model,
        aggregate: { score_mean: data.confidence },
        judgments: []
      }],
      winner: { model: data.winner_model, score: data.confidence }
    };
    
    return new Response(JSON.stringify(transformedResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error('🚨 Request failed:', error);
    return new Response(
      JSON.stringify({ 
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
        debug: "Check backend logs and ensure authentication is configured"
      }), 
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}