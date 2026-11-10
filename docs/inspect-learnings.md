# Inspect learnings

- The agent loop runs in Inspect, in the `.venv` process. Inspect calls the model API from there, not from the container.
- The Docker container only runs commands. It never calls the model API, unless an agent is installed inside it.
- Tools such as `bash()` are defined and dispatched by Inspect. Only the command itself runs in the container.
- Every tool result goes back into the conversation, so the model sees the output on its next turn.
- Model-graded scorers also call a model, from Inspect's process.
- Built-in sandbox tools include `bash()`, `bash_session()`, `python()`, and `text_editor()`.
- The Inspect sandboxing docs don't include a diagram of the tool-call flow. The diagrams in this repo represent my interpretation.

## Design choices

- The code the agent debugs (the task and its data) must be in the container. The agent's `bash()` and `python()` commands only see files that exist there.
- The Inspect task code (the task, solver, and scorer `.py` files) stays on the host in `.venv`. It doesn't go into the container.
- A scorer that runs tests through `sandbox().exec()` checks the container's files. A scorer that only compares output to an expected value can run on the host.
- The agent can change anything in the container, so the scorer should check results in a way the agent can't tamper with.

## Security

- Keep host folders out of the container. Copy in only the ETL code and data the task needs. Mount anything else read-only.
- Never mount the Docker socket or run the container with `--privileged`.
- Keep `.env` and API keys on the host. Inspect makes the model calls from the host, so the agent doesn't need them.
- The sandbox has no network by default. When Inspect writes the compose file, from its default image or the task's Dockerfile, it sets `network_mode: none`. A task that supplies its own compose file must set this itself.
- Set memory, CPU, and process limits in the compose file.
- Set `time_limit` and `message_limit` on the task so a stuck agent stops on its own.
- Run the container as a non-root user.
- Watch long runs with `uv run inspect view --log-dir logs`. If possible, run them on a spare machine or VM.
- Keep the task's starting files in git so you can restore them if the agent breaks the pipeline.
- Docker Desktop on macOS runs containers in a Linux VM. That adds a layer, but don't rely on it alone.

## Running in AWS

Options, roughly from simplest to most isolated:

- **EC2 instance running Docker.** A dedicated VM you start for a run and terminate afterward. Closest to the local setup. This repo's `terraform/` folder sets one up.
- **ECS on Fargate.** Each container runs as a managed task in its own microVM, a stronger boundary than a shared-kernel container.
- **Kubernetes (EKS).** Inspect supports Kubernetes sandboxes. Worth it only if you already run clusters.
- **Hosted sandboxes.** Inspect has extensions for Modal and Daytona. Not yet checked for setup or cost.

Running in AWS keeps the agent off your machine, but it isn't automatically safer:

- **Credentials are the main risk.** Give the instance no IAM role, or one with only the permissions it needs. Require IMDSv2 with a hop limit of 1 so containers can't reach the metadata service.
- **Network.** No inbound access, or SSH from your IP only. Allow outbound traffic only where the run needs it.
- **Cost.** Set a budget alarm and make the instance stop itself after the run. The model API costs far more than the instance: about $0.44 for 4 hours on an `m7i.large`, versus possibly tens of dollars of model calls.
- **Data.** Don't attach buckets with real data unless the task needs them.
- **Access.** With no IAM role and no inbound access, you can't reach the instance to start the eval or copy logs off. Allow SSH from your own IP only.

## Deploying to EC2

Terraform creates the instance and installs Docker, the Compose plugin, git, tmux, rsync, and uv. The rest is done by hand over SSH.

1. **Create the instance.** Set `ssh_cidr` (your IP with `/32`) and `key_name` in `terraform/terraform.tfvars`, run `terraform apply`, and SSH in with the `ssh_command` output.
2. **Copy the repo over.** From your laptop:

   ```sh
   rsync -av --exclude .venv --exclude logs ./ ec2-user@<ip>:~/inspect-experiments/
   ```

   Or clone a public repo over HTTPS. A `git@github.com:` clone fails, because the security group only allows outbound ports 80 and 443. Don't put a personal GitHub token on the instance.
3. **Set up the environment.** Run `cd ~/inspect-experiments && uv sync`. Copy `.env` over, or export the API key for the session only. The key stays on the instance, not in the container.
4. **Build the sandbox and run.** Inspect builds the container with `docker compose` on the first run. The Dockerfile's `COPY` lines put the ETL code and data into the image. Run the eval inside tmux so it survives a dropped SSH connection:

   ```sh
   tmux new -s eval
   uv run inspect eval tasks/... --model ...
   ```

5. **Watch it and get the results.** Run `uv run inspect view --log-dir logs` on the instance. On your laptop, run `ssh -L 7575:localhost:7575 ec2-user@<ip>` and open `http://localhost:7575` (7575 is Inspect's default port). Copy logs back with:

   ```sh
   rsync -av ec2-user@<ip>:~/inspect-experiments/logs/ ./logs/
   ```

6. **Tear down.** Run `terraform destroy`. This deletes the instance, the disk, the `.env` file, and any logs you didn't copy back.

## Working with the EC2 instance from your laptop

1. **Add an SSH config entry.** Put this in `~/.ssh/config`:

   ```
   Host inspect-eval
       HostName <public_ip>
       User ec2-user
       IdentityFile ~/.ssh/<your-key>.pem
       LocalForward 7575 localhost:7575
       ServerAliveInterval 60
   ```

   Then `ssh inspect-eval` connects, opens the `inspect view` tunnel, and keeps idle connections alive. The tools below use this entry.
2. **Use VS Code Remote-SSH for daily work.** Connect to `inspect-eval` to edit files, run a terminal, and browse logs on the instance. Install the Inspect AI extension on the remote side too. You still copy or clone the repo there once.
3. **Run long evals in tmux.** Reattach with `ssh inspect-eval` and `tmux attach -t eval`. VS Code's terminal doesn't survive a disconnect, so use tmux there too.
4. **Copy logs back with rsync** before `terraform destroy`.

Things that trip you up:

- **Your IP changes.** On a new network, SSH times out. Update `ssh_cidr` and run `terraform apply`.
- **The instance's IP changes.** After the self-shutdown stops the instance, a restart gives it a new public IP. Update `HostName`, or use an Elastic IP to keep the address fixed.
- **SSH-free access needs a role.** AWS Systems Manager Session Manager works with no inbound port, but it needs an IAM role on the instance.

## Running in GitHub Codespaces

Moved to [github-codespace.md](github-codespace.md): the dev container, setup, running evals with tmux, viewing logs, long runs, cost, and troubleshooting.

Compared with EC2, Codespaces is easier to set up and use. EC2 gives you control over the network and has no idle timeout, so it's better for runs longer than about 4 hours.

## Inspect compared with agent frameworks

Inspect has the core pieces of an agent framework such as LangChain, LangGraph, Bedrock AgentCore, or Strands Agents. It's built to test agents, not to run them in production.

- **Shared features:** an agent loop (`react()`), tools defined with `@tool`, one interface across model providers, multi-agent handoffs, and full tracing in `inspect view`.
- **Eval features:** datasets, scorers, epochs, limits on time, messages, and tokens, and throwaway sandboxes.
- **Not covered:** large integration libraries, graph workflows with saved state, and production hosting.
- **Agent bridge:** Inspect can run an agent built in another framework and score it. A common pattern is to build the agent elsewhere and evaluate it in Inspect.
- For this repo, Inspect alone is enough, because the agent only needs to exist for the eval.
