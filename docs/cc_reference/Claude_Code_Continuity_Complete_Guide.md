# Claude Code 24/7 Continuity - Complete Implementation Guide

## Overview

Claude Code hooks enable true 24/7 autonomous operation through strategic use of lifecycle events and the `stop_hook_active` flag. This system allows for controlled session restarts without infinite loops.

## Core Concepts

### 1. Hook System Architecture

**Stop Hook Mechanism:**
- Fires when Claude Code session ends
- Receives JSON payload with `stop_hook_active` boolean flag
- Enables ONE controlled restart per session to prevent infinite loops

**Hook Payload Structure:**
```json
{
  "session_id": "abc123",
  "transcript_path": ".../session.jsonl",
  "hook_event_name": "Stop",
  "stop_hook_active": false  // Key flag for loop prevention
}
```

### 2. The stop_hook_active Flag Logic

**First Stop Event:** `stop_hook_active: false`
- Safe to restart session exactly once
- Hook script can invoke `claude code -c -p "Continue"`

**Second Stop Event:** `stop_hook_active: true`
- Already restarted once - EXIT IMMEDIATELY
- Prevents infinite restart loops
- Script should `exit 0`

### 3. Basic Stop Hook Implementation

```bash
#!/usr/bin/env bash
# ~/.claude/hooks/stop_hook.sh

# Read JSON payload from stdin
read -r payload
active=$(jq -r '.stop_hook_active' <<< "$payload")

if [ "$active" = "false" ]; then
  # First time Stop → safe to restart
  claude code -c -p "Continuing 24/7 run"
else
  # Already restarted once → exit to avoid loop
  exit 0
fi
```

**Configuration in ~/.claude/settings.json:**
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/stop_hook.sh"
          }
        ]
      }
    ]
  }
}
```

## Deployment Variations for 24/7 Operation

### Variation 1: In-Terminal Shell Loop
**Best for:** Quick testing, single terminal sessions

```bash
#!/usr/bin/env bash
# run_cc_continuous.sh
TARGET_DIR="/path/to/project"
PROMPT="Continue 24/7 run"
DELAY=5

cd "$TARGET_DIR" || exit 1
echo "▶ Starting continuous Claude Code..."

while true; do
  claude code -c -p "$PROMPT"
  echo "🔄 Restarting in ${DELAY}s..."
  sleep "$DELAY"
done
```

### Variation 2: systemd Service
**Best for:** Linux servers, auto-start at boot

```ini
# /etc/systemd/system/claude-continuous.service
[Unit]
Description=Claude Code 24/7 Continuous Runner
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/claude code -c -p "Start continuous run"
Restart=always
RestartSec=5
StartLimitBurst=5
StartLimitIntervalSec=60

[Install]
WantedBy=multi-user.target
```

**Management:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable claude-continuous
sudo systemctl start claude-continuous
sudo journalctl -u claude-continuous -f
```

### Variation 3: Docker Container
**Best for:** Containerized environments

```dockerfile
FROM node:18
RUN npm install -g @anthropics/claude-code
WORKDIR /app
CMD ["sh", "-c", "while true; do claude code -c -p 'Continue run'; sleep 5; done"]
```

```bash
docker build -t cc-continuous .
docker run -d --name cc-runner --restart always -v /path/to/project:/app cc-continuous
```

### Variation 4: Kubernetes Deployment
**Best for:** Scalable container orchestration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cc-continuous
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cc-continuous
  template:
    metadata:
      labels:
        app: cc-continuous
    spec:
      containers:
      - name: cc-runner
        image: cc-continuous:latest
        command: ["/app/run_cc.sh"]
        volumeMounts:
        - name: project
          mountPath: /app
```

## Event-Driven Architecture

### Redis/DragonflyDB Integration

**Subscriber Script:**
```bash
#!/usr/bin/env bash
# start_claude_listener.sh
REDIS_CHANNEL="claude-trigger"
TARGET_DIR="/path/to/project"

launch_claude() {
  msg="$1"
  gnome-terminal -- bash -lc "
    cd \"$TARGET_DIR\" \
    && echo '>> Launching Claude Code: \"$msg\"' \
    && claude code -c -p \"$msg\"; \
    exec bash
  "
}

# Subscribe and dispatch
redis-cli subscribe "$REDIS_CHANNEL" | while read -r line; do
  if [[ $line =~ ^message[[:space:]]+$REDIS_CHANNEL[[:space:]]+(.+)$ ]]; then
    payload=${BASH_REMATCH[1]}
    launch_claude "$payload"
  fi
done
```

**Publishing Events:**
```bash
# Redis
redis-cli publish claude-trigger "Build and test suite"

# Redpanda (Kafka CLI)
rpk topic produce claude-trigger <<<'{"msg":"Run nightly analysis"}'
```

## JSON Streaming for Programmatic Control

### Input/Output Formats

**JSON Input Mode:**
```bash
echo '{"query":"Run security audit"}' \
  | claude code -c \
      --input-format stream-json \
      --output-format stream-json \
      --max-turns 5
```

**Output Streaming:**
- `--output-format stream-json` emits NDJSON events
- Each event represents: user messages, assistant replies, tool calls, results
- Perfect for real-time parsing and automation

### Automated Pipeline Example
```bash
#!/usr/bin/env bash
cd /path/to/project
DELAY=5

while true; do
  # Generate or fetch next JSON command
  cmd_json=$(next_command_generator)  # e.g., voice-to-text → JSON

  # Pipe JSON input, stream JSON output
  echo "$cmd_json" \
    | claude code -c \
        --input-format stream-json \
        --output-format stream-json \
        --max-turns 10 \
    >> claude_session.log

  echo "🔄 Restarting in ${DELAY}s…"
  sleep $DELAY
done
```

## Speech-to-Speech Integration

### Architecture Overview
```
[ Client ] ≤WebRTC/WebSocket⇒ [ STT Server ] ⇒ JSON transcript ⇒ [ Message Broker ]
                                                       ↓
                                              [ Claude Code Listener ]
                                                       ↓
                                              JSON response text ⇒ [ TTS Server ]
                                                       ↓
                                         Audio stream via WebSocket ⇒ [ Client ]
```

### Self-Hosted STT/TTS Options

**Speech-to-Text:**
- **OpenAI Whisper**: ~200ms/chunk, near-human accuracy, ≥16GB VRAM
- **Vosk (Kaldi)**: <50ms/chunk, good accuracy, modest GPU requirements
- **ESPnet2**: ~100ms/chunk, excellent accuracy, ≥12GB VRAM

**Text-to-Speech:**
- **Coqui TTS (VITS)**: Very high quality, real-time, ≥12GB VRAM
- **FastSpeech 2 + HiFi-GAN**: High quality, real-time, ≥8GB VRAM
- **Tacotron 2 + WaveGlow**: High quality, ~0.5× real-time, ≥16GB VRAM

### iPhone Integration Options

#### Option 1: PWA (No Developer Account)
- Progressive Web App installable via Safari
- WebRTC for audio capture/playback
- WebSocket streaming to STT/TTS services
- "Add to Home Screen" for native-like experience

#### Option 2: Native iOS App (Requires $99/yr Developer Account)
- Full AVFoundation access for low-latency audio
- Background audio processing capabilities
- gRPC-Swift for efficient streaming
- SiriKit integration possible
- App Store distribution

**Native iOS Development:**
```swift
// Audio capture example
let engine = AVAudioEngine()
let input = engine.inputNode
let format = input.outputFormat(forBus: 0)

input.installTap(onBus: 0, bufferSize: 4096, format: format) { buffer, _ in
  // Convert buffer to PCM and send over gRPC stream
}

engine.prepare()
try engine.start()
```

## Best Practices

### 1. Loop Prevention
- ALWAYS check `stop_hook_active` in Stop hooks
- Exit immediately when flag is `true`
- Only restart when flag is `false`

### 2. Configuration Management
- Global hooks: `~/.claude/settings.json`
- Project-specific: `.claude/settings.json`
- Version control hook scripts for team consistency

### 3. Monitoring & Logging
- Redirect JSON streams to log files: `>> claude_session.log`
- Use `-n` line numbers in output mode for debugging
- Implement health checks in automation scripts

### 4. Error Handling
- Set appropriate restart delays to avoid rate limits
- Monitor exit codes and implement exponential backoff
- Use `--dangerously-skip-permissions` for unattended runs (if safe)

### 5. Resource Management
- Use `--max-turns` to bound session length
- Implement log rotation for long-running sessions
- Monitor memory usage in containerized deployments

## Advanced Features

### Multiple Agent Orchestration
- Use frameworks like `claudecode-orchestrator`
- Manage sub-agent lifecycles with hooks
- Evidence collection and validation workflows
- Parallel execution with coordination

### Integration Patterns
- GitButler for branch-isolated development
- CI/CD pipeline automation
- Real-time monitoring and alerting
- Custom event-driven workflows

## Security Considerations

- Use HTTPS for all external communications
- Implement API key authentication
- Restrict hook execution permissions
- Audit log all automated actions
- Use TLS for gRPC communications
- Implement rate limiting on public endpoints

This system enables true 24/7 autonomous Claude Code operation with controlled restarts, event-driven triggers, and comprehensive deployment options for any infrastructure setup.