# Safety and cost

The precautions this repo follows when running evals, and how it keeps costs down. For background and other options, see [inspect-learnings.md](inspect-learnings.md).

## Security precautions

### Where models run

- **No real model calls on a laptop.** Local runs use only `--model mockllm/model`, which makes no network calls and needs no key.
- **Real model runs happen only in the cloud,** which for now means a GitHub Codespace. A codespace is a separate VM, so an agent run never touches your own machine.
- **No API keys in the repo or on your laptop.** Keys are stored only as Codespaces secrets, such as `GOOGLE_API_KEY`, limited to this repo. This is the guarantee that matters most: without a key, a local model call fails, whoever starts it. See [API keys](../README.md#api-keys).
- **The same rules are written for Claude Code** in [CLAUDE.md](../CLAUDE.md), so it runs only the mock model locally and never writes a key to a file.

### What the sandbox can reach

- **No network.** Inspect writes the sandbox's compose file with `network_mode: none`, so the agent can't download anything or send data out. See [How Inspect picks the sandbox image](eval-architecture.md#how-inspect-picks-the-sandbox-image).
- **No host files.** Nothing from the host is mounted into the sandbox. The agent only sees what the Dockerfile copies in.
- **No keys.** The model is called by Inspect outside the sandbox, so keys never enter the container.
- **A fresh container for each sample,** removed afterward, so one run can't affect the next.
- **A non-root user.** `fix_syntax` runs as an `agent` user that owns only `/workspace`. `hello_docker` uses Inspect's default image, which runs as root. That's acceptable for an `echo` check, but not for agent tasks.

### Keeping the answers out of reach

- **The answer key stays on the host.** The expected output is in the task's `.py` file, which runs outside the sandbox, so the agent can't read or change it.
- **The reference solution never enters the sandbox,** except on purpose with `-T solution=reference`. A `.dockerignore` allow-list hides everything but `sandbox/` from the Docker build, so even a `COPY .` line couldn't pull in `solution/` or the answer key.

### Gaps

- **Partial run limits.** `fix_syntax` sets `message_limit=30`, so a stuck agent stops on its own. No task sets a `time_limit` or `token_limit` yet. Longer agent tasks should set all three.

## Cost-saving measures

### Test without a model first

- **Use the mock model** to check that a task runs: `--model mockllm/model` is free.
- **Test scorers with reference solutions.** `-T solution=reference` should score 1, and `-T solution=none` should score 0. Both run without a model, so a broken scorer is caught before any paid run.

### Keep paid runs small

- **Start with a cheap model,** such as a Gemini Flash model, to check the task and transcript. Move to stronger models once the task works.
- **Limit samples** with `--limit`, for example `--limit 5`, on first runs.
- **Add epochs only when needed.** Each epoch repeats every sample, so 3 epochs cost 3 times as much. Use them to measure consistency, not to debug.
- **Keep tool output short.** Every call resends the whole conversation, so a large command output is paid for again on every later turn. See [Where the conversation comes from](agent-sandbox-sequence.md#where-the-conversation-comes-from).

### Keep cloud costs at zero

- **Use the Codespaces free tier.** Personal accounts get a monthly allowance of core-hours and storage. A 2-core machine is enough for these tasks. Check GitHub's billing docs for current limits.
- **Stop or delete codespaces when you're done.** A stopped codespace still uses storage, and a deleted one uses nothing.

### Gaps

- **Partial spending limits.** The message limit on `fix_syntax` caps how long a run can go, but not its exact cost. A `token_limit` would cap that more directly. Set a spending limit or budget alert with each model provider too.
