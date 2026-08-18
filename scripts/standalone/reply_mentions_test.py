#!/usr/bin/env python3
import sys
import os

# Ensure the plugins directory is in sys.path
sys.path.insert(0, '/c/Users/downl/Documents/New project/hermes-agent/plugins')

# Import the core module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    'core',
    '/c/Users/downl/Documents/New project/hermes-agent/plugins/lm-twitterer/core.py'
)

if spec is None:
    print('Failed to create spec')
    sys.exit(1)
    
mod = importlib.util.module_from_spec(spec)

# Execute the module
spec.loader.exec_module(mod)

# Call the function
result = mod.handle_reply_mentions({
    'dry_run': False,
    'count': 50,
    'mark_seen_on_dry_run': False,
    'provider': 'moa',
    'model': 'hakuapulse-orchestrator'
})

print(mod._json(result))