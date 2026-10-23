"""Insert actual, escaped C01 source excerpts into the architecture walkthrough."""
from pathlib import Path
from html import escape
from textwrap import dedent
import re

APP=Path(__file__).resolve().parents[1]
server=(APP/'server.js').read_text(encoding='utf-8')
browser=(APP/'public/app.js').read_text(encoding='utf-8')
agent=(APP/'scripts/create-agent.js').read_text(encoding='utf-8')
environment=(APP/'scripts/create-environment.js').read_text(encoding='utf-8')
page=APP/'public/architecture.html'
html=page.read_text(encoding='utf-8')
html=re.sub(r'\n?\s*<!-- walkthrough-code:[^>]+ -->.*?<!-- /walkthrough-code -->', '', html, flags=re.S)
html=html.replace('<section class="student-section" aria-labelledby="walkthrough-title">',
                  '<section id="walkthrough" class="student-section" aria-labelledby="walkthrough-title">')
html=html.replace('class="architecture-branches"','class="architecture-branches with-code"')


def excerpt(source,start,end,include_end=False):
    at=source.index(start)
    stop=source.index(end,at)+(len(end) if include_end else 0)
    line_start=source.rfind('\n',0,at)+1
    prefix=source[line_start:at]
    return dedent((prefix if not prefix.strip() else '')+source[at:stop]).strip()


def example(label,code,explanation):
    return ('\n<figure class="code-example">\n'
            '<figcaption>'+escape(label)+' · source excerpt</figcaption>\n'
            '<pre><code class="language-javascript">'+escape(code)+'</code></pre>\n'
            '<p class="code-explanation">'+escape(explanation)+'</p>\n</figure>\n')


blocks={
 'Create the remote session · arrows 1–6':[
     ('public/app.js · New session button',
      excerpt(browser,'const session = await api("/api/sessions"','    notice("Session created.'),
      'The browser asks the local server to create the session, then passes the returned ID to connect(). It does not call Anthropic directly.'),
     ('server.js · create a managed session',
      excerpt(server,'const session = await client.beta.sessions.create({','    try {'),
      'The host selects the configured agent and environment. The budget amount is expressed in cents: "50" means 50¢ of USD list cost.')],
 'Prepare observation · arrows 7–11':[
     ('server.js · attach(): open stream, then read history',
      excerpt(server,'const stream = await client.beta.sessions.events.stream(id);','  sessions.set(id, state);'),
      'The stream opens first so live delivery can be buffered while history is fetched. If reading history fails, the host aborts this stream and surfaces the error.'),
     ('server.js · emit(): deduplicate and retain records',
      excerpt(server,'function emit(state, event) {','async function attach(id)'),
      'seen prevents repeated IDs from being forwarded twice. The events array supports replay to the browser, and listeners receive SSE text. These collections live only in host memory.')],
 'Connect the browser feed · arrows 12–14':[
     ('server.js · return the created session',
      excerpt(server,'    try {\n      await attach(session.id);','  }\n  const match = url.pathname.match('),
      'The create route prepares the host reader before returning the session. If attachment fails after creation, it reports the created session ID rather than pretending creation never happened.'),
     ('public/app.js · browser EventSource',
      excerpt(browser,'  source = new EventSource(', '  source.onerror ='),
      'This opens the browser-to-host SSE connection. The controls become enabled on connection, and incoming records are passed to showEvent().'),
     ('server.js · browser SSE endpoint',
      excerpt(server,'    if (req.method === "GET" && operation === "stream") {','    if (req.method === "POST" && operation === "message")'),
      'The host first replays its buffered records, then keeps this HTTP response in its listener set. Closing the browser connection removes that listener; it does not interrupt the remote session.')],
 'Send a prompt · arrows 15–18':[
     ('public/app.js · submit the message',
      excerpt(browser,'    await api(`/api/sessions/${id}/message`','    $("message").value ='),
      'The browser sends JSON to the local message endpoint. The current session ID keeps the prompt in the same conversation.'),
     ('server.js · validate message text',
      excerpt(server,'      const data = await body(req);\n      if (\n        typeof data.text', '      await attach(id);'),
      'The host rejects missing, empty, or oversized text before asking the provider to do work.'),
     ('server.js · attach before sending user.message',
      excerpt(server,'      await attach(id);\n      await client.beta.sessions.events.send', '      return json(res, 200, { ok: true });'),
      'attach() reuses an existing host reader or opens one before sending. The SDK receives a user.message event containing the trimmed prompt.')],
 'Observe the response · arrows 19–21':[
     ('server.js · consume live provider events',
      excerpt(server,'      for await (const event of stream) emit(state, event);','      emit(state, {'),
      'The host consumes the SDK stream and sends each event through the same emit() function used for history.'),
     ('public/app.js · render message text',
      excerpt(browser,'    const content = document.createElement("p");','    item.append(content);',True),
      'Inside the agent.message/user.message branch, the page creates a paragraph and assigns textContent, so returned text is displayed as text rather than interpreted as HTML.'),
     ('public/app.js · read an idle event',
      excerpt(browser,'  if (event.type === "session.status_idle") {','    $("reasonHelp").textContent ='),
      'The displayed stop reason comes from the event. The following code maps that reason to an explanation; idle alone does not mean the requested business result is verified.')],
 'Keep the session ID and reconnect':[
     ('public/app.js · remember the connected session',
      excerpt(browser,'  try {\n    sessionStorage.setItem','  $("reason").textContent ='),
      'connect() remembers the ID in this browser tab. Storage failures are tolerated so the lab still works when browser storage is unavailable.'),
     ('public/app.js · restore the ID on return',
      excerpt(browser,'try {\n  const previousSession = sessionStorage.getItem','api("/api/config")'),
      'Returning from the guide or architecture page fills the session field and asks the student to click Connect. This code does not create a session, reconnect, or send a prompt automatically.'),
     ('public/app.js · explicitly reconnect',
      excerpt(browser,'$("connect").onclick = () => {','$("messageForm").onsubmit'),
      'The student chooses when to reconnect. connect() validates the ID and opens the browser EventSource shown in step 3.'),
     ('server.js · reuse an existing reader',
      excerpt(server,'async function attach(id) {','  // Open first:'),
      'If the host still has the reader, it reuses it. Otherwise attach() continues with the stream-before-history sequence shown in step 2.')],
 'Pending tool action':[
     ('server.js · construct the matching response event',
      excerpt(server,'      let event;\n      if (data.result === "custom")', '      return json(res, 200, { ok: true });'),
      'The validated action chooses between a custom tool result and a tool confirmation. Both reference the matching pending event ID; supplying a result and granting approval are different operations.')],
 'Interrupt and inspect':[
     ('server.js · send the interrupt request',
      excerpt(server,'    if (req.method === "POST" && operation === "interrupt") {','    if (req.method === "POST" && operation === "action")'),
      'A successful local response means the interrupt event was sent. This handler does not poll or confirm that the remote session has stopped.'),
     ('server.js · inspect the remote session',
      excerpt(server,'    if (req.method === "GET" && !operation)','    if (req.method === "GET" && operation === "stream")'),
      'Inspect session retrieves the current provider record. Read its remote state, or wait for an appropriate status event, before concluding that work has stopped.')]
}

for number,(title,examples) in enumerate(blocks.items(),1):
    anchor='<h3>'+title+'</h3>'
    start=html.index(anchor)
    end=html.index('</div></li>' if number<=6 else '</article>',start)
    snippets='\n<!-- walkthrough-code:'+str(number)+' -->'+''.join(example(*item) for item in examples)+'<!-- /walkthrough-code -->\n'
    html=html[:end]+snippets+html[end:]

setup={
 'Install dependencies and configure the API key':(
     'scripts/create-agent.js · shared setup pattern',
     excerpt(agent,'require("dotenv").config','(async () => {'),
     'dotenv loads the local .env file. The script checks the API key and constructs the SDK client. create-environment.js uses the same setup pattern; neither script puts the key in browser code.'),
 'Create the agent configuration':(
     'scripts/create-agent.js · create and report the agent ID',
     excerpt(agent,'  const agent = await client.beta.agents.create({','  console.log("Copy this value into .env.");',True),
     'name identifies the configuration, model selects its model, system supplies instructions, and tools enables the built-in toolset. agents.create returns the new agent ID for later session creation. This call does not send a user message.'),
 'Create the environment configuration':(
     'scripts/create-environment.js · create and report the environment ID',
     excerpt(environment,'  const environment = await client.beta.environments.create({','  console.log("Copy this value into .env.");',True),
     'The cloud configuration selects limited networking while enabling its package-manager exception. environments.create returns a reusable environment ID. Creating this record is separate from creating and observing a session.')
}
for number,(title,item) in enumerate(setup.items(),1):
    start=html.index('<h3>'+title+'</h3>')
    end=html.index('</div></li>',start)
    snippet='\n<!-- walkthrough-code:setup'+str(number)+' -->'+example(*item)+'<!-- /walkthrough-code -->\n'
    html=html[:end]+snippet+html[end:]

page.write_text(html,encoding='utf-8')
print(f'Added {sum(map(len,blocks.values()))+len(setup)} source excerpts across setup, six runtime steps, and two optional branches.')
