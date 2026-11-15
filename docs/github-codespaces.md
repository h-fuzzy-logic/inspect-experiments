# GitHub Codespaces

Real model runs happen only in the cloud, and for now that means a GitHub Codespace. A Codespace is a cloud VM that runs this repo in a dev container. It needs no Terraform, SSH setup, or copying the repo, and an agent run never touches your own machine. See [Safety and cost](safety-and-cost.md) for why.

This page has everything about Codespaces: setup, API keys, getting the latest code, running evals, viewing logs, and troubleshooting.

## What's in the dev container

The setup is in `.devcontainer/`:

- **`Dockerfile`:** Microsoft's Python 3.11 dev container image (`mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`), with:
  - the base image's Yarn package source removed, because it fails signature checks and breaks the build
  - tmux, to keep long evals running if VS Code disconnects
  - uv, copied in so it's on the PATH before any terminal opens
- **`devcontainer.json`:**
  - the `docker-in-docker` feature, so Inspect can start sandbox containers inside the Codespace
  - `uv sync` when the Codespace is created
  - the Python and Inspect AI extensions
  - port 7575 (the log viewer) forwarded

A Codespace runs two images, one inside the other:

```
Codespace (devcontainers/python image)
├── Inspect, uv, .venv, logs/
└── Docker (docker-in-docker)
    └── Sandbox (aisiuk/inspect-tool-support)
        └── echo hello from docker
```

- **The Codespace image** is set in `.devcontainer/Dockerfile`. Inspect, uv, `.venv`, and the logs live here. It plays the role your laptop plays locally.
- **The sandbox image** is where the agent's commands run. `hello_docker` uses Inspect's default image, because its folder has no Docker files. A task with its own `Dockerfile`, such as `fix_syntax`, builds its own image instead. See [How Inspect picks the sandbox image](eval-architecture.md#how-inspect-picks-the-sandbox-image).

## Set up

1. **Add each API key as a Codespaces secret.** Click your profile picture, then go to **Settings → Codespaces → Secrets → New secret**. Name it for the provider, such as `ANTHROPIC_API_KEY` for Claude or `GOOGLE_API_KEY` for Gemini, and limit its **Repository access** to this repo. GitHub sets the secret as an environment variable in the Codespace, and Inspect reads it from there. Never put a key in a file.
2. **Set the idle timeout to the maximum,** 240 minutes, in the same settings page. It may only apply to Codespaces created after you change it.
3. **Create a new Codespace** from `main`: on the repo page, click **Code → Codespaces → Create codespace**. A 2-core machine is enough for the current tasks. The first build takes a few minutes. To watch it, run **Codespaces: View Creation Log** from the Command Palette.
4. **Open it in VS Code on your Mac,** not in the browser. On github.com/codespaces, click **…** next to the Codespace, then **Open in Visual Studio Code**. VS Code will offer to install the **GitHub Codespaces** extension.
5. **Check the setup** in the Codespace terminal:

   ```sh
   uv --version
   docker info --format '{{.ServerVersion}}'
   printenv | cut -d= -f1 | grep API_KEY
   ```

   The first two should print versions. The third should list the names of your keys, such as `ANTHROPIC_API_KEY`. It shows only the names, never the values.

6. **Check a Gemini model answers** (optional):

   ```sh
   scripts/check_model.sh list
   scripts/check_model.sh gemini-3.6-flash
   ```

   The first lists the Gemini models your key can use, which is free. The second sends one short prompt and prints the status code and how long the reply took. The script uses `GOOGLE_API_KEY` only, and refuses to run outside a Codespace.

A secret added or changed after the Codespace started isn't visible until you stop and restart the Codespace.

## Get the latest code

A Codespace is its own clone of the repo. Nothing syncs between it and your Mac by itself:

```text
Mac (local edits) --git push--> GitHub --git pull--> Codespace
```

Each time you change code locally and want to run it in the Codespace, push from your Mac, then in the Codespace run:

```sh
git pull
git log -1 --oneline
```

Check that `git log` shows the commit you expect before spending credits on a run. Each eval log records the commit it ran on. Run `uv sync` too if `pyproject.toml` or `uv.lock` changed. Docker rebuilds a task's image by itself when its `Dockerfile` changes.

A new Codespace clones the branch as it is when it's created, so it starts with the latest pushed code.

## Run an eval

Start long runs inside tmux, so they keep going if VS Code disconnects, such as when your screen locks:

```sh
tmux new -s eval
```

Check the task without a model first, which is free. Expect accuracies of 1 and then 0. The first command also builds the task's sandbox image, and shows its progress while it does:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=reference --model mockllm/model
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=none --model mockllm/model
```

Then run the task's tests. `-v` prints each test as it finishes, so you can see progress. Expect `19 passed, 4 xfailed`:

```sh
uv run pytest tasks/fix_syntax/tests -v
```

Then run with a model, starting with 2 samples:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model anthropic/claude-haiku-5-5 --limit 2 --max-connections 2 --time-limit 600 --attempt-timeout 180
```

Then the full eval, as in the [fix_syntax results](../tasks/fix_syntax/RESULTS.md#reproduce):

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model anthropic/claude-haiku-5-5 --epochs 3 --max-connections 2 --time-limit 600 --attempt-timeout 180
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model anthropic/claude-sonnet-5-5 --epochs 3 --max-connections 2 --time-limit 600 --attempt-timeout 180
```

Check the provider's current model list for exact model names. Each run costs a little.

- **`--limit`** runs only the first few samples. **`--sample-id`** runs one sample by its ID, such as `--sample-id missing_comma`.
- **`--epochs`** runs each sample that many times.
- **`--max-connections`** caps how many model requests run at once. On a free tier, use 1 to stay under the rate limit.
- **`--time-limit`** stops the sample after that many seconds, so a stuck run ends on its own.
- **`--attempt-timeout`** abandons a model request that hasn't answered in time, then retries it. Without it, Inspect waits on a silent request forever, because model requests have no timeout by default.
- **`--max-retries`** (optional) gives up after that many retries and shows the error. Leave it out on a free tier: Inspect waits and retries when it hits the rate limit, and a low limit makes the run give up when a short wait would have worked.

tmux keys all start with Ctrl+B. Press it, let go, then press the next key:

| Keys | What it does |
|---|---|
| Ctrl+B, then D | Detach: leave the session running in the background |
| Ctrl+B, then C | Open a new window in the session, such as for `docker ps` while a run is going |
| Ctrl+B, then N | Switch to the next window |

After you reconnect, run `tmux attach -t eval` to see the session again, or `tmux ls` to list sessions. Ctrl+C works inside tmux the same as anywhere else.

If tmux isn't available, `nohup` also keeps a run going after a disconnect:

```sh
nohup uv run inspect eval tasks/fix_syntax/fix_syntax.py --model anthropic/claude-haiku-5-5 --time-limit 600 > tmp/eval.out 2>&1 &
```

## How many Docker containers run

Inside the Codespace, Inspect uses Docker to build images and start containers. An image is the template, and a container is one running copy of it.

- **One image per task.** For `fix_syntax`, Docker pulls `python:3.12-slim`, then builds the task's image from its `Dockerfile`. This happens on the first run only. Later runs reuse the image until the Dockerfile changes. `hello_docker` has no Dockerfile, so it pulls Inspect's default image, `aisiuk/inspect-tool-support`, instead.
- **A new Codespace starts with no images,** so its first run pulls and builds again. That's why the first run in a new Codespace is slow.
- **One container per sample.** Each sample, and each epoch of it, gets a fresh container from the task's image, which Inspect removes when the sample finishes. A full `fix_syntax` eval with 3 epochs starts 24 containers.
- **How many run at once.** Two limits apply, and the lower one wins:
  - Inspect runs as many samples at once as `--max-connections` allows. With `--max-connections 2`, that's two samples, and two containers, at a time.
  - Inspect caps Docker sandboxes at twice the machine's CPU count. On a 2-core Codespace, that's 4 containers at once.
- **The test suite starts many containers,** from the same image: one per sample for each of the all-sample tests, and one for each scorer edge-case test. On a 2-core Codespace, this takes a few minutes. On a laptop, it takes about 35 seconds.

To see what Docker is doing, open a second tmux window (Ctrl+B, then C) and run:

```sh
docker images
docker ps
```

`docker images` lists the images that have been built or pulled. `docker ps` lists the containers running right now.

## View logs

- **Inspect AI extension:** click any `.eval` file in `logs/`. If it doesn't open in the viewer, run **Python: Select Interpreter**, choose `.venv/bin/python`, then run **Developer: Reload Window**.
- **`inspect view`:** run `uv run inspect view --log-dir logs`, and open port 7575 from the **Ports** tab. With VS Code on your Mac, the port is forwarded to `localhost`, which is the only address the viewer trusts by default. In a browser-based Codespace, the viewer may refuse with "Invalid host header" or "Forbidden browser origin." In that case, run `gh codespace ports forward 7575:7575` on your laptop and open `http://localhost:7575`.
- **Download logs:** right-click `logs/` in the Explorer and choose **Download**, then copy them into `logs/` on your Mac to build results there. Do this before deleting the Codespace, because `logs/` is git-ignored and isn't saved anywhere else.
- **Read a log as JSON:** `uv run inspect log dump <file>.eval > tmp/log.json`.

## Long runs

- **A disconnect doesn't stop the Codespace,** but it can stop a program running in a VS Code terminal. Use tmux.
- **The idle timeout may not count a running eval as activity.** Codespaces measures activity as you interacting with it, so a long run can be stopped partway. Set the timeout to 240 minutes, and check in on long runs.
- **Runs longer than about 4 hours don't fit Codespaces.** Use an EC2 instance instead. See [Running in AWS](inspect-learnings.md#running-in-aws).

## Cost

- **Machine size:** a 2-core machine is enough for the current tasks. A 4-core, 16 GB machine should fit the ETL task.
- **Free tier:** personal accounts get a monthly allowance, about 120 core-hours and 15 GB of storage on GitHub Free, and 180 core-hours and 20 GB on GitHub Pro. These numbers are from memory and GitHub changes them, so check its billing docs.
- **Stop or delete Codespaces when you're done.** A running Codespace uses core-hours until the idle timeout, and a stopped one still uses storage.

## Security

- **API keys** live only in Codespaces secrets, which GitHub sets as environment variables in the Codespace.
- **The Codespace has a GitHub token** with access to the repo, and open outbound network access. The sandbox container gets neither: it doesn't get the token unless you pass it in, and it has no network by default.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| A rebuild still fails, or uses old settings | **Codespaces: Rebuild Container** uses the Codespace's own copy of the files, not GitHub's. Delete the Codespace and create a new one from `main`. |
| The build fails with `dl.yarnpkg.com … is not signed` | The base image's Yarn source. `.devcontainer/Dockerfile` removes it, so this only happens with an old copy of the files. Create a new Codespace. |
| `uv: command not found` | The Codespace was built from an old config. uv is now in the image. Create a new Codespace. |
| An API key seems to be missing | Check with `printenv \| cut -d= -f1 \| grep API_KEY`. If it's really missing, stop and restart the Codespace. Secrets load only at startup, and reloading the window isn't enough. Then open a new terminal. |
| A command does something strange, or prints "command not found" for text | The paste was changed on the way into the terminal. Type the command, or use a script such as `scripts/check_model.sh`. Also check you're in the Codespace window: its bottom-left corner shows **Codespaces**. |
| `No inspect tasks were found`, or a run used old code | The Codespace doesn't have the latest files. See [Get the latest code](#get-the-latest-code). |
| Files display in a small box with their own scrollbar | Safari has display problems with browser-based Codespaces. Open the Codespace in VS Code on your Mac instead. |
| `Quota exceeded … generate_content_free_tier_requests, limit: 5` | Gemini's free tier allows only 5 requests per minute for this model, and each agent turn is one request. Changing timeouts won't help. Either slow Inspect down with `--max-connections 1`, a longer `--time-limit`, and no low `--max-retries` (Inspect waits and retries on its own), or enable billing for much higher limits. See [Cap spending with each model provider](safety-and-cost.md#cap-spending-with-each-model-provider). |
| The tests or an eval seem stuck, with no output | Usually slow, not stuck. pytest prints nothing until the end unless you add `-v`, and the first run in a new Codespace pulls and builds the image. Run the `-T solution=reference` eval first, which shows its progress, then the tests with `-v`. To check Docker, open a second tmux window (Ctrl+B, then C) and run `docker ps`. If it lists containers, it's working. If `docker info` hangs, restart the Codespace. See [How many Docker containers run](#how-many-docker-containers-run). |
| Ctrl+C doesn't stop a run | Inspect stops its containers before it exits, which can take a while. Press Ctrl+C again and wait about 30 seconds. If it's still stuck, open a second tmux window (Ctrl+B, then C) and run `pkill -f pytest` or `pkill -f "inspect eval"`, or end the whole session with `tmux kill-session -t eval`. |
| Containers are left over after a stopped run | Run `uv run inspect sandbox cleanup docker`, which removes every container Inspect started. `docker ps` should then list none. |
| An eval seems stuck while "generating" | The model is slow or rate-limited. For Gemini, time it with `scripts/check_model.sh <model>`. Two minutes per reply is the model, not your setup. Try another model, and use `--attempt-timeout` and `--time-limit`. |
| A run scored `C` but shows `model call cancelled` | A time limit cut off the run after the agent had already fixed the file. The scorer checks the file, not whether the agent submitted. Check the sample's limit field. |
