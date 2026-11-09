# Local synthetic evaluation on the M1 Mac

Implementation is ready; installation, model download, actual memory/speed and disconnected
generation are **unverified** in this session. `ollama` was absent from PATH and
`/Applications/Ollama.app` did not exist. No generation or paid API request occurred.
The one authorized local twelve-case run has not been consumed.

The selected model is exactly [`qwen3.5:4b-q4_K_M`](https://ollama.com/library/qwen3.5:4b-q4_K_M),
verified on 2026-10-18: about 3.3 GB, 4.21B main model parameters, Q4_K_M, with mixed higher
precision tensors and a separate BF16 vision projector. It is not Qwen3 4B, the default
Qwen3.5 tag, an MLX variant, a cloud tag, or a model with a different quantization.
The registry displayed manifest prefix `d8b0f5e9760c`; the actual full installed digest is
recorded by preflight, because tags can move. Do not substitute a different model if setup fails.

[Ollama's macOS requirements](https://docs.ollama.com/macos) are macOS 14+ and Apple M series
for CPU/GPU support. This host reports arm64 and macOS 26.1; 16 GB unified memory is the
human-supplied hardware specification, not a measured peak-use result. Model file size is
not total memory use: runtime, context cache, projector and other apps add overhead.
Disk inspection reported approximately 24 GiB available, but no installation allocation
was tested. Runtime support is verified against installed metadata, not assumed from download success.

1. **While connected to the internet**, download Ollama from the
   [official macOS download](https://ollama.com/download/mac), mount its DMG, and drag
   Ollama into Applications. This is the remaining interactive installation step;
   macOS may require an approval to open the signed binary or install a CLI link.
   No administrator shell command or API key is needed for the experiment itself.
   Avoid launching the GUI; quit it if it starts. Use the bundled CLI directly by
   adding its documented directory to PATH in each terminal:

   ```sh
   export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
   ```

2. In Terminal A, start a preparation server with cloud disabled and explicit loopback
   binding. Keep this terminal open. A port conflict is a blocker: stop your own old
   preparation server rather than connecting to an unknown daemon or changing the bind.

   ```sh
   OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11435 \
     OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
     OLLAMA_CONTEXT_LENGTH=12288 ollama serve
   ```

   Confirm the log contains `Ollama cloud disabled: true` and
   `Listening on 127.0.0.1:11435`. These controls come from the
   [official FAQ](https://docs.ollama.com/faq). Do not expose the server to your LAN.

3. In Terminal B, set PATH as in step 1 and download **only** the approved tag. The
   pull requires internet and disk space. It does not generate a tutor response.

   ```sh
   OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen3.5:4b-q4_K_M
   ```

   Wait for a successful download. Do not run a separate `ollama run` smoke test:
   the authorized twelve-case experiment below is also the generation check.
   Press Control-C in Terminal A to stop the preparation server and release port 11435.
   Keep the downloaded model in the same user's normal Ollama store. If using a custom
   `OLLAMA_MODELS` directory, export that same value for preparation and evaluation.

4. **Disconnect the internet before generation**: turn Wi-Fi off in macOS Control
   Center and unplug any Ethernet/USB network or tethering connection. Do not rely
   on a VPN or the cloud-disabled flag as proof of disconnection. Leave loopback
   networking available. Confirm there is no active external network connection in
   System Settings → Network. The agent could not perform or observe this step;
   it must be verified by the operator.

5. From the repository root in Terminal B (with the same PATH), execute **once**:

   ```sh
   .venv/bin/python -m experiments.tutor_v1.local \
     --network-disconnected \
     --output artifacts/tutor-v1-local-qwen35-first-disconnected.jsonl
   ```

   This CLI starts its own fresh cloud-disabled loopback server and shuts it down on
   exit. It never downloads, accesses a hosted inference endpoint, requests credentials,
   or uses the Luna adapter. The flag records **OPERATOR_ATTESTED**, not an automated
   network test. Omit it if you cannot attest to step 4; the evidence then says UNVERIFIED.
   If the output path already exists, it fails before starting the server: preserve it.
   Do not rerun completed or failed cases without another instruction. A setup failure
   with zero generation requests does not create a real-model baseline.

6. While running, observe Activity Monitor → Memory for memory pressure and swap,
   and note other applications and whether the laptop is warm/throttling. The evidence
   records loaded-model `size`/`size_vram`, actual context, prompt/generated counts,
   nanosecond load/prompt/generation durations and wall elapsed seconds where available.
   Those values are not whole-system peak memory. Tokens/sec can be derived as
   `eval_count * 1e9 / eval_duration` when duration is positive. The first case includes
   cold loading; there is no extra warmup request. No measured M1 performance is claimed yet.

7. Review the new evidence: a runtime record must identify the installed tag/full
   digest/Q4_K_M/runtime version; each valid case must show complete JSON and
   `VALID_REPLY_SHAPE`. Check the summary's generation request count and any
   NOT_EXECUTED cases. Success while you have verified step 4 establishes observed
   disconnected generation on that setup. If blocked, retain the evidence and report
   the failure instead of changing models, tuning the prompt, reducing budgets or retrying.

The native [chat API](https://docs.ollama.com/api/chat) uses top-level `think=false`,
`stream=false` and the exact existing JSON reply schema; generation options set
`num_predict=1000` and `num_ctx=12288`. The [parameter reference](https://docs.ollama.com/modelfile)
defines `num_predict` as the maximum generated-token budget, including formatting rather
than only visible reply text. Thinking can use generation budget when enabled; the baseline
requests it disabled, verifies advertised support and rejects returned thinking. Missing
thinking metadata is a setup blocker, not permission to assume it is disabled.

The 30-second generation deadline remains unchanged and includes loading. A timeout halts
the remaining run, records failures/skips, and shuts down its owned server. It is not an
automatic retry. Report observed timing before proposing a different deadline or budget;
neither is automatically adjusted. Structural JSON validation establishes mechanics only.
Leave all six instructional judgments pending for the human and learning assistant.

All input-admission assumptions, output accounting and runtime checks are specified in
[ai-runtime.md](../../docs/ai-runtime.md#local-ollama-baseline--offline-eval-003).
The 1,024-token framing reserve is deliberately conservative but unmeasured; this is a
Qwen-specific assumption checked against available actual counts, not reuse of the
OpenAI estimator or a guarantee for arbitrary tokenizers, templates or multimodal content.
