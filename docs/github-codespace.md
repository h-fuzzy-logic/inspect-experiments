# GitHub Codespaces

Real model runs happen only in the cloud, and for now that means a GitHub Codespace. A codespace is a cloud VM that runs this repo in a dev container. It needs no Terraform, SSH setup, or copying the repo, and an agent run never touches your own machine. See [Safety and cost](safety-and-cost.md) for why.

## What's in the dev container

The setup is in `.devcontainer/`:

- **`Dockerfile`:** Microsoft's Python 3.11 dev container image (`mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`), with:
  - the base image's Yarn package source removed, because it fails signature checks and breaks the build
  - tmux, to keep long evals running if VS Code disconnects
  - uv, copied in so it's on the PATH before any terminal opens
- **`devcontainer.json`:**
  - the `docker-in-docker` feature, so Inspect can start sandbox containers inside the codespace
  - `uv sync` when the codespace is created
  - the Python and Inspect AI extensions
  - port 7575 (the log viewer) forwarded

A codespace runs two images, one inside the other:

```
Codespace (devcontainers/python image)
├── Inspect, uv, .venv, logs/
└── Docker (docker-in-docker)
    └── Sandbox (aisiuk/inspect-tool-support)
        └── echo hello from docker
```

- **The codespace image** is set in `.devcontainer/Dockerfile`. Inspect, uv, `.venv`, and the logs live here. It plays the role your laptop plays locally.
- **The sandbox image** is where the agent's commands run. `hello_docker` uses Inspect's default image, because its folder has no Docker files. A task with its own `Dockerfile`, such as `fix_syntax`, builds its own image instead. See [How Inspect picks the sandbox image](eval-architecture.md#how-inspect-picks-the-sandbox-image).

## Set up

1. **Add the API key as a Codespaces secret.** Click your profile picture, then go to **Settings → Codespaces → Secrets → New secret**. Name it for the provider, such as `GOOGLE_API_KEY` for Gemini, and limit its **Repository access** to this repo. Never put a key in a file.
2. **Set the idle timeout to the maximum,** 240 minutes, in the same settings page. It may only apply to codespaces created after you change it.
3. **Create a new codespace** from `main`: on the repo page, click **Code → Codespaces → Create codespace**. A 2-core machine is enough for the current tasks. The first build takes a few minutes. To watch it, run **Codespaces: View Creation Log** from the Command Palette.
4. **Open it in VS Code on your Mac,** not in the browser. On github.com/codespaces, click **…** next to the codespace, then **Open in Visual Studio Code**. VS Code will offer to install the **GitHub Codespaces** extension.
5. **Check the setup** in the codespace terminal:

   ```sh
   uv --version
   docker info --format '{{.ServerVersion}}'
   printenv | cut -d= -f1 | grep GOOGLE_API_KEY
   ```

   The first two should print versions. The third should print `GOOGLE_API_KEY`. It shows only the variable's name, never its value.

6. **Check the model answers:**

   ```sh
   scripts/check_model.sh list
   scripts/check_model.sh gemini-3.6-flash
   ```

   The first lists the Gemini models your key can use, which is free. The second sends one short prompt and prints the status code and how long the reply took. The script refuses to run outside a codespace.

## Run an eval

Start long runs inside tmux, so they keep going if VS Code disconnects, such as when your screen locks:

```sh
tmux new -s eval
```

Check the task without a model first, which is free. Expect accuracies of 1 and then 0:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=reference --model mockllm/model
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=none --model mockllm/model
```

Then run with the model:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model google/gemini-3.6-flash --time-limit 600 --attempt-timeout 180
```

- **`--time-limit`** stops the sample after that many seconds, so a stuck run ends on its own.
- **`--attempt-timeout`** abandons a model request that hasn't answered in time, then retries it. Without it, Inspect waits on a silent request forever, because model requests have no timeout by default.
- **`--max-retries`** (optional) gives up after that many retries and shows the error. Leave it out on a free tier: Inspect waits and retries when it hits the rate limit, and a low limit makes the run give up when a short wait would have worked.

To leave the tmux session running, press Ctrl+B, then D. After you reconnect, run `tmux attach -t eval` to see it again.

If tmux isn't available, `nohup` also keeps a run going after a disconnect:

```sh
nohup uv run inspect eval tasks/fix_syntax/fix_syntax.py --model google/gemini-3.6-flash --time-limit 600 > tmp/eval.out 2>&1 &
```

## View logs

- **Inspect AI extension:** click any `.eval` file in `logs/`. If it doesn't open in the viewer, run **Python: Select Interpreter**, choose `.venv/bin/python`, then run **Developer: Reload Window**.
- **`inspect view`:** run `uv run inspect view --log-dir logs`, and open port 7575 from the **Ports** tab. With VS Code on your Mac, the port is forwarded to `localhost`, which is the only address the viewer trusts by default. In a browser-based codespace, the viewer may refuse with "Invalid host header" or "Forbidden browser origin." In that case, run `gh codespace ports forward 7575:7575` on your laptop and open `http://localhost:7575`.
- **Download logs:** right-click `logs/` in the Explorer and choose **Download**. Do this before deleting the codespace, because `logs/` is git-ignored and isn't saved anywhere else.
- **Read a log as JSON:** `uv run inspect log dump <file>.eval > tmp/log.json`.

## Long runs

- **A disconnect doesn't stop the codespace,** but it can stop a program running in a VS Code terminal. Use tmux.
- **The idle timeout may not count a running eval as activity.** Codespaces measures activity as you interacting with it, so a long run can be stopped partway. Set the timeout to 240 minutes, and check in on long runs.
- **Runs longer than about 4 hours don't fit Codespaces.** Use an EC2 instance instead. See [Running in AWS](inspect-learnings.md#running-in-aws).

## Cost

- **Machine size:** a 2-core machine is enough for the current tasks. A 4-core, 16 GB machine should fit the ETL task.
- **Free tier:** personal accounts get a monthly allowance, about 120 core-hours and 15 GB of storage on GitHub Free, and 180 core-hours and 20 GB on GitHub Pro. These numbers are from memory and GitHub changes them, so check its billing docs.
- **Stop or delete codespaces when you're done.** A running codespace uses core-hours until the idle timeout, and a stopped one still uses storage.

## Security

- **API keys** live only in Codespaces secrets, which GitHub sets as environment variables in the codespace.
- **The codespace has a GitHub token** with access to the repo, and open outbound network access. The sandbox container gets neither: it doesn't get the token unless you pass it in, and it has no network by default.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| A rebuild still fails, or uses old settings | **Codespaces: Rebuild Container** uses the codespace's own copy of the files, not GitHub's. Delete the codespace and create a new one from `main`. |
| The build fails with `dl.yarnpkg.com … is not signed` | The base image's Yarn source. `.devcontainer/Dockerfile` removes it, so this only happens with an old copy of the files. Create a new codespace. |
| `uv: command not found` | The codespace was built from an old config. uv is now in the image. Create a new codespace. |
| `GOOGLE_API_KEY` seems to be missing | Check with `printenv \| cut -d= -f1 \| grep GOOGLE_API_KEY`. If it's really missing, stop and restart the codespace. Secrets load only at startup, and reloading the window isn't enough. Then open a new terminal. |
| A command does something strange, or prints "command not found" for text | The paste was changed on the way into the terminal. Type the command, or use a script such as `scripts/check_model.sh`. Also check you're in the codespace window: its bottom-left corner shows **Codespaces**. |
| `No inspect tasks were found` | The codespace doesn't have the latest files. Run `git pull`, then `uv sync`. |
| Files display in a small box with their own scrollbar | Safari has display problems with browser-based codespaces. Open the codespace in VS Code on your Mac instead. |
| `Quota exceeded … generate_content_free_tier_requests, limit: 5` | Gemini's free tier allows only 5 requests per minute for this model, and each agent turn is one request. Changing timeouts won't help. Either slow Inspect down with `--max-connections 1`, a longer `--time-limit`, and no low `--max-retries` (Inspect waits and retries on its own), or enable billing for much higher limits. See [Cap spending with each model provider](safety-and-cost.md#cap-spending-with-each-model-provider). |
| An eval seems stuck while "generating" | The model is slow or rate-limited. Time it with `scripts/check_model.sh <model>`. Two minutes per reply is the model, not your setup. Try another model, and use `--attempt-timeout` and `--time-limit`. |
| A run scored `C` but shows `model call cancelled` | A time limit cut off the run after the agent had already fixed the file. The scorer checks the file, not whether the agent submitted. Check the sample's limit field. |
