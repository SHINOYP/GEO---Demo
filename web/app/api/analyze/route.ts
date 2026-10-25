import { NextRequest, NextResponse } from "next/server";
import { runAnalyze } from "@/lib/pythonBridge";

export async function POST(req: NextRequest) {
  let body: { url?: unknown; html?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: true, kind: "validation", message: "Request body must be JSON." },
      { status: 400 },
    );
  }

  const url = typeof body.url === "string" ? body.url.trim() : "";
  const html = typeof body.html === "string" && body.html.length > 0 ? body.html : undefined;

  if (!url || !/^https?:\/\//.test(url)) {
    return NextResponse.json(
      { error: true, kind: "validation", message: "url must start with http:// or https://" },
      { status: 400 },
    );
  }

  try {
    const result = await runAnalyze(url, html);
    return NextResponse.json(result.body, { status: result.status });
  } catch (err) {
    return NextResponse.json(
      {
        error: true,
        kind: "internal",
        message: `Could not start the analysis engine: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 500 },
    );
  }
}
