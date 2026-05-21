import { type NextRequest, NextResponse } from "next/server";

const BACKEND = "http://217.216.34.228:8000";

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const target = `${BACKEND}/${path.join("/")}`;
  const url = new URL(req.url);
  const dest = url.search ? `${target}${url.search}` : target;

  const headers = new Headers();
  headers.set("content-type", req.headers.get("content-type") || "application/json");

  const init: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.body && !["GET", "HEAD"].includes(req.method)) {
    init.body = await req.text();
  }

  const upstream = await fetch(dest, init);
  const body = await upstream.arrayBuffer();

  return new NextResponse(body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: {
      "content-type": upstream.headers.get("content-type") || "application/json",
    },
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
