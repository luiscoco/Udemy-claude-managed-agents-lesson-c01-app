require("dotenv").config({ quiet: true });
const Anthropic = require("@anthropic-ai/sdk");
if (
  !process.env.ANTHROPIC_API_KEY ||
  process.env.ANTHROPIC_API_KEY === "your_api_key"
) {
  console.error("Set ANTHROPIC_API_KEY in .env before running this command.");
  process.exit(1);
}
const client = new Anthropic();
(async () => {
  console.log("Creating agent in your Anthropic workspace...");
  const agent = await client.beta.agents.create({
    name: "Session Lab Agent",
    model: "claude-sonnet-4-6",
    system: "You are a helpful assistant.",
    tools: [{ type: "agent_toolset_20260401" }],
  });
  console.log("CLAUDE_MANAGED_AGENT_ID=" + agent.id);
  console.log("Copy this value into .env.");
})().catch((error) => {
  console.error("Could not create agent:", error.message);
  process.exitCode = 1;
});
