import { NextRequest, NextResponse } from "next/server";
import { runReport } from "@/lib/pythonBridge";
import type { AnalysisResult } from "@/lib/types";

export async function POST(req: NextRequest) {
  let analysis: AnalysisResult;
  try {
    analysis = await req.json();
  } catch {
    return NextResponse.json(
      { error: true, kind: "validation", message: "Request body must be JSON." },
      { status: 400 },
    );
  }

  try {
    const result = await runReport(analysis);
    if (!result.ok) {
      return NextResponse.json(result.body, { status: result.status });
    }
    const filename = `citelytics_report_${Date.now()}.pdf`;
    return new NextResponse(new Uint8Array(result.body), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: true,
        kind: "internal",
        message: `Could not start the report engine: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 500 },
    );
  }
}
