require("dotenv").config({ quiet: true });
const Anthropic = require("@anthropic-ai/sdk");

if (!process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY === "your_api_key") {
  console.error("Set ANTHROPIC_API_KEY in .env before running this command.");
  process.exit(1);
}

(async () => {
  const agent = await new Anthropic().beta.agents.create({
    name: "Session Lab Pending Action Demo",
    model: "claude-sonnet-4-6",
    system: "For requests about the demo fact, call get_demo_fact. For the approval demonstration, use the bash tool to run the requested harmless command. Explain the result to the user.",
    tools: [
      {
        type: "custom",
        name: "get_demo_fact",
        description: "Ask the application for a demonstration fact about a topic.",
        input_schema: {
          type: "object",
          properties: { topic: { type: "string", description: "The requested topic." } },
          required: ["topic"],
        },
      },
      { type: "agent_toolset_20260401", default_config: { permission_policy: { type: "always_ask" } } },
    ],
  });
  console.log("CLAUDE_MANAGED_AGENT_ID=" + agent.id);
  console.log("For the pending-action demo, copy this ID into .env and restart the server. Save your previous agent ID first.");
})().catch((error) => {
  console.error("Could not create demo agent:", error.message);
  process.exitCode = 1;
});
