---
allowed-tools: Bash
description: Register this Nova with the ecosystem
---

# 🌐 Nova Registration

Registering with the Nova ecosystem...

!python3 -c "
import os
import sys
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src')

from nova_registry import NovaRegistry

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🌐 Registering Nova: {nova_id}')

# Define capabilities based on Nova ID
capabilities_map = {
    'torch': ['development', 'coordination', 'monitoring', 'code_generation'],
    'tester': ['testing', 'validation', 'feedback', 'quality_assurance'],
    'forge': ['infrastructure', 'deployment', 'session_management'],
    'echo': ['communication', 'logging', 'alerting'],
    'sage': ['analysis', 'optimization', 'learning']
}

capabilities = capabilities_map.get(nova_id, ['general'])

# Register
registry = NovaRegistry(nova_id)
registry.register(capabilities, {
    'version': '1.0.0',
    'environment': 'development'
})

print(f'✅ Registered with capabilities: {capabilities}')

# Discover other Novas
print('\\n🔍 Discovering other Novas...')
discovered = registry.discover()

if discovered:
    print(f'Found {len(discovered)} active Nova(s):')
    for nova in discovered:
        print(f'  - {nova[\"nova_id\"]}: {nova[\"capabilities\"]}')
else:
    print('  No other Novas found yet')

# Get network status
status = registry.get_network_status()
print(f'\\n📊 Network Status:')
print(f'  Total Active: {status[\"active_novas\"]}')
print(f'  Pending Tasks: {status[\"total_pending_tasks\"]}')
print(f'  Network Health: {status[\"network_health\"]}')
"

## Next Steps:
- Other Novas will discover you automatically
- Your capabilities determine which tasks you receive
- Heartbeat keeps you registered (every 30s)