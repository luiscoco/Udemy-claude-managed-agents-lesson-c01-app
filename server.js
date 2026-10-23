const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
require("dotenv").config();
const Anthropic = require("@anthropic-ai/sdk");
const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY || "not-configured",
});
const sessions = new Map();
const port = Number(process.env.PORT || 3000);
function json(res, code, data) {
  res.writeHead(code, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(data));
}
async function body(req) {
  let data = "";
  for await (const chunk of req) {
    data += chunk;
    if (data.length > 65536) throw new Error("Request too large");
  }
  return data ? JSON.parse(data) : {};
}
function emit(state, event) {
  if (event.id && state.seen.has(event.id)) return;
  if (event.id) state.seen.add(event.id);
  state.events.push(event);
  const line = `data: ${JSON.stringify(event)}\n\n`;
  for (const res of state.listeners) res.write(line);
}
async function attach(id) {
  if (sessions.has(id)) return sessions.get(id);
  // Open first: events produced while history loads remain buffered in the SDK stream.
  const stream = await client.beta.sessions.events.stream(id);
  const state = { events: [], seen: new Set(), listeners: new Set(), stream };
  try {
    for await (const event of client.beta.sessions.events.list(id))
      emit(state, event);
  } catch (error) {
    stream.controller.abort();
    throw error;
  }
  sessions.set(id, state);
  (async () => {
    try {
      for await (const event of stream) emit(state, event);
      emit(state, {
        type: "app.stream_closed",
        message: "Live stream closed. Reconnect to refresh.",
      });
    } catch (error) {
      emit(state, { type: "app.stream_error", message: error.message });
    } finally {
      sessions.delete(id);
      for (const listener of state.listeners) listener.end();
    }
  })();
  return state;
}
async function main(req, res) {
  const url = new URL(req.url, "http://localhost");
  if (req.method === "GET" && url.pathname === "/api/config")
    return json(res, 200, {
      configured: Boolean(
        process.env.ANTHROPIC_API_KEY &&
        process.env.CLAUDE_MANAGED_AGENT_ID &&
        process.env.CLAUDE_MANAGED_ENVIRONMENT_ID,
      ),
    });
  if (req.method === "POST" && url.pathname === "/api/sessions") {
    if (
      !process.env.ANTHROPIC_API_KEY ||
      !process.env.CLAUDE_MANAGED_AGENT_ID ||
      !process.env.CLAUDE_MANAGED_ENVIRONMENT_ID
    )
      return json(res, 400, {
        error:
          "Configure ANTHROPIC_API_KEY, CLAUDE_MANAGED_AGENT_ID, and CLAUDE_MANAGED_ENVIRONMENT_ID in .env.",
      });
    const session = await client.beta.sessions.create({
      agent: process.env.CLAUDE_MANAGED_AGENT_ID,
      environment_id: process.env.CLAUDE_MANAGED_ENVIRONMENT_ID,
      budget: {
        type: "limit",
        max_list_cost: { amount: "50", currency: "USD" },
      },
    });
    try {
      await attach(session.id);
    } catch (error) {
      return json(res, 502, {
        error: `Session ${session.id} was created, but its stream could not be opened: ${error.message}`,
        sessionId: session.id,
      });
    }
    return json(res, 201, session);
  }
  const match = url.pathname.match(
    /^\/api\/sessions\/(sesn_[A-Za-z0-9_-]+)(?:\/(stream|message|interrupt|action))?$/,
  );
  if (match) {
    const [, id, operation] = match;
    if (req.method === "GET" && !operation)
      return json(res, 200, await client.beta.sessions.retrieve(id));
    if (req.method === "GET" && operation === "stream") {
      const state = await attach(id);
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      });
      res.write(": connected\n\n");
      for (const event of state.events)
        res.write(`data: ${JSON.stringify(event)}\n\n`);
      state.listeners.add(res);
      req.on("close", () => state.listeners.delete(res));
      return;
    }
    if (req.method === "POST" && operation === "message") {
      const data = await body(req);
      if (
        typeof data.text !== "string" ||
        !data.text.trim() ||
        data.text.length > 20000
      )
        return json(res, 400, {
          error: "Enter a message of up to 20,000 characters.",
        });
      await attach(id);
      await client.beta.sessions.events.send(id, {
        events: [
          {
            type: "user.message",
            content: [{ type: "text", text: data.text.trim() }],
          },
        ],
      });
      return json(res, 200, { ok: true });
    }
    if (req.method === "POST" && operation === "interrupt") {
      await client.beta.sessions.events.send(id, {
        events: [{ type: "user.interrupt" }],
      });
      return json(res, 200, { ok: true });
    }
    if (req.method === "POST" && operation === "action") {
      const data = await body(req);
      if (
        typeof data.id !== "string" ||
        !data.id ||
        !["allow", "deny", "custom"].includes(data.result)
      )
        return json(res, 400, { error: "Provide an event ID and action." });
      let event;
      if (data.result === "custom") {
        if (typeof data.text !== "string" || !data.text.trim())
          return json(res, 400, { error: "Enter the custom tool result." });
        event = {
          type: "user.custom_tool_result",
          custom_tool_use_id: data.id,
          content: [{ type: "text", text: data.text }],
        };
      } else
        event = {
          type: "user.tool_confirmation",
          tool_use_id: data.id,
          result: data.result,
        };
      await client.beta.sessions.events.send(id, { events: [event] });
      return json(res, 200, { ok: true });
    }
  }
  if (
    req.method === "GET" &&
    ["/", "/guide.html", "/architecture.html", "/architecture.svg", "/architecture.png", "/app.js", "/navigation.js", "/style.css", "/astronaut.png"].includes(url.pathname)
  ) {
    const name = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
    res.writeHead(200, {
      "Content-Type": name.endsWith(".svg")
        ? "image/svg+xml; charset=utf-8"
        : name.endsWith(".png")
        ? "image/png"
        : name.endsWith(".html")
        ? "text/html; charset=utf-8"
        : name.endsWith(".css")
          ? "text/css; charset=utf-8"
          : "text/javascript; charset=utf-8",
    });
    return fs.createReadStream(path.join(__dirname, "public", name)).pipe(res);
  }
  json(res, 404, { error: "Not found" });
}
http
  .createServer((req, res) =>
    main(req, res).catch((error) => {
      if (!res.headersSent)
        json(res, error.status || 500, { error: error.message });
      else res.end();
    }),
  )
  .listen(port, "127.0.0.1", () =>
    console.log(`Listening on http://127.0.0.1:${port}`),
  );
