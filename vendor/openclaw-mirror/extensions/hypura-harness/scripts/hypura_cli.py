# /// script
# dependencies = ["requests", "httpx", "click"]
# ///
import httpx
import click
import json
import sys

# ASI_ACCEL: Hypura CLI Bridge (OpenClaw Empowerment)
# Fulfilling SOUL.md Directive: Infinite Interface / Tool Sovereignty

HARNESS_URL = "http://127.0.0.1:18794"

@click.group()
def cli():
    """Hypura Harness CLI — Unified control for ASI Hakua."""
    pass

@cli.command()
@click.argument('text')
@click.option('--emotion', default='neutral', help='VOICEVOX emotion')
@click.option('--speaker', default=8, help='VOICEVOX speaker ID')
def speak(text, emotion, speaker):
    """Manifest voice output via VOICEVOX."""
    try:
        r = httpx.post(f"{HARNESS_URL}/speak", json={
            "text": text,
            "emotion": emotion,
            "speaker": speaker
        }, timeout=10.0)
        click.echo(r.json())
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.argument('text')
def chatbox(text):
    """Send text to VRChat Chatbox."""
    try:
        r = httpx.post(f"{HARNESS_URL}/osc", json={
            "action": "chatbox",
            "payload": {"text": text}
        })
        click.echo(r.json())
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.argument('query')
def scavenge(query):
    """Trigger an intent-driven web scavenge."""
    try:
        r = httpx.post(f"{HARNESS_URL}/scavenge", json={"query": query})
        click.echo(r.json())
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.argument('concept')
def wisdom(concept):
    """Query the associative knowledge graph."""
    try:
        r = httpx.post(f"{HARNESS_URL}/wisdom", json={"concept": concept})
        click.echo(r.json())
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def status():
    """Check harness and substrate health."""
    try:
        r = httpx.get(f"{HARNESS_URL}/status")
        click.echo(json.dumps(r.json(), indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    cli()
