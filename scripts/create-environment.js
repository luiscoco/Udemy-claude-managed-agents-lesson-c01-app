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
  console.log("Creating environment in your Anthropic workspace...");
  const environment = await client.beta.environments.create({
    name: "Session Lab Environment",
    config: {
      type: "cloud",
      networking: { type: "limited", allow_package_managers: true },
    },
  });
  console.log("CLAUDE_MANAGED_ENVIRONMENT_ID=" + environment.id);
  console.log("Copy this value into .env.");
})().catch((error) => {
  console.error("Could not create environment:", error.message);
  process.exitCode = 1;
});
