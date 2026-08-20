import json
import random
from datetime import datetime


# seed42: deterministic random seed for reproducible topic selection
random.seed(42)

# Predefined greeting topics for A2A agent coordination
GREETING_TOPICS = [
    "daily-status-check",
    "resource-alignment",
    "timing-sync",
    "workflow-optimization",
    "status-update",
]

# A2A agent endpoints dictionary
# Secretary bot runs on port 9902 per main config
A2A_AGENTS = {
    "main-agent": "http://127.0.0.1:9900",
    "secretary": "http://127.0.0.1:9902",
    "sedori-buyer": "http://127.0.0.1:9911",
    "sedori-ledger": "http://127.0.0.1:9916",
    "sedori-lister": "http://127.0.0.1:9913",
    "sedori-researcher": "http://127.0.0.1:9912",
    "sedori-secretary": "http://127.0.0.1:9914",
    "sedori-shipper": "http://127.0.0.1:9915",
    "delivery-worker": "http://127.0.0.1:9909",
}

# NIM keys for round-robin A2A agent routing
NIM_KEYS = [
    {"model": "nvidia/nemotron-3.5-lightning-30b-a3b", "provider": "nvidia", "api_key": "[REDACTED]"},
    {"model": "nvidia/nemotron-3.5-lightning-30b-a3b", "provider": "nvidia", "api_key": "[REDACTED]"},
]

# Coordinator proposal mappings by topic
COORDINATION_PROPOSALS = {
    "daily-status-check": "Let's synchronize our daily status updates and share any blockers or progress.",
    "resource-alignment": "I propose we align our resource allocations for the upcoming period. Could you share your current resource usage and priorities?",
    "timing-sync": "Let's verify our timing synchronization. Are there any scheduled tasks or events we should coordinate around?",
    "workflow-optimization": "I'd like to explore workflow optimization opportunities between our agents. What tasks could be streamlined or delegated more efficiently?",
    "status-update": "Please provide a brief status update for the secretary's memory log. What's your current state, any pending work, and estimated completion times?",
}


def select_random_topic(offset=0):
    """Select a random topic using seed42 for reproducible results.
    
    Args:
        offset: Integer offset added to seed for variation across multiple calls.
    
    Returns:
        str: One of the GREETING_TOPICS, reproducibly selected.
    """
    topics_copy = GREETING_TOPICS.copy()
    random.seed(42 + offset)
    random.shuffle(topics_copy)
    return topics_copy[0]


def generate_greeting(topic, target_agent):
    """Generate a greeting message for a target A2A agent.
    
    Args:
        topic: The greeting topic from GREETING_TOPICS.
        target_agent: The A2A agent endpoint identifier (e.g., 'main-agent', 'sedori-buyer').
    
    Returns:
        dict: Greeting message with role, content, and metadata.
    """
    metadata = {
        "seed": 42,
        "topic": topic,
        "agent": "secretary",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"),
    }
    
    content = f"""🤖 Secretary Bot Greeting

Topic: {topic}
Target: {target_agent}
Seed: 42 (reproducible)

Hello! I'm the secretary bot with seed42 memory base. I'm reaching out regarding '{topic}' for coordination purposes. How are you functioning, and would you like to synchronize on any upcoming tasks or resource allocations?"""
    
    return {
        "role": "assistant",
        "content": content,
        "metadata": metadata,
    }


def generate_coordination_proposal(topic, target_agents):
    """Generate a coordination proposal based on the greeting topic.
    
    Args:
        topic: The greeting topic from GREETING_TOPICS.
        target_agents: List of target agent identifiers.
    
    Returns:
        dict: Coordination proposal with topic, proposal text, and metadata.
    """
    proposal = COORDINATION_PROPOSALS.get(
        topic,
        "Let's coordinate on alignment and optimization.",
    )
    
    return {
        "topic": topic,
        "proposal": proposal,
        "target_agents": target_agents,
        "agent": "secretary",
        "seed": 42,
        "reproducible": True,
    }


def greet_agents(target_agents=None, num_greetings=3):
    """Generate greetings for specified A2A agents.
    
    Args:
        target_agents: List of agent identifiers to greet. If None, uses default agents.
        num_greetings: Number of greetings to generate (defaults to 3).
    
    Returns:
        list: List of greeting dictionaries, each containing target, topic, greeting, and coordination_proposal.
    """
    if target_agents is None:
        target_agents = list(A2A_AGENTS.keys())
    
    greetings = []
    for i in range(min(num_greetings, len(target_agents))):
        target = target_agents[i % len(target_agents)]
        topic = select_random_topic(offset=i)
        greeting = generate_greeting(topic, target)
        coordination = generate_coordination_proposal(topic, [target])
        
        greetings.append({
            "target": target,
            "topic": topic,
            "greeting": greeting,
            "coordination_proposal": coordination,
        })
    
    return greetings


def coordinate_agents(target_agents=None, num_coordinations=3):
    """Generate coordination proposals for A2A agents.
    
    Args:
        target_agents: List of agent identifiers to coordinate with.
        num_coordinations: Number of coordination proposals to generate.
    
    Returns:
        list: List of coordination proposal dictionaries.
    """
    if target_agents is None:
        target_agents = list(A2A_AGENTS.keys())
    
    coordinations = []
    for i in range(min(num_coordinations, len(target_agents))):
        target = target_agents[i % len(target_agents)]
        # Use greeting to determine topic
        from secretary_bot import select_random_topic
        topic = select_random_topic(offset=i)
        proposal = generate_coordination_proposal(topic, [target])
        
        coordinations.append({
            "target": target,
            "topic": topic,
            "proposal": proposal,
        })
    
    return coordinations


def get_status():
    """Report current bot status and memory state.
    
    Returns:
        dict: Status dictionary with seed, configured agents, and current state.
    """
    return {
        "agent": "secretary",
        "port": 9902,
        "seed": 42,
        "status": "active",
        "greeting_topics": GREETING_TOPICS,
        "a2a_agents": A2A_AGENTS,
        "nim_keys_configured": len(NIM_KEYS),
        "reproducible": True,
    }


def main():
    """Main entry point for secretary bot operations."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python secretary_bot.py <greet|coordinate|status>")
        print("\nCommands:")
        print("  greet    - Send greetings to A2A agents with random topics")
        print("  coordinate - Generate coordination proposals")
        print("  status   - Report current bot status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "greet":
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        greetings = greet_agents(num_greetings=num)
        print(json.dumps({"command": "greet", "greetings": greetings}, ensure_ascii=False, indent=2))
    
    elif command == "coordinate":
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        coordinations = coordinate_agents(num_coordinations=num)
        print(json.dumps({"command": "coordinate", "coordinations": coordinations}, ensure_ascii=False, indent=2))
    
    elif command == "status":
        status = get_status()
        print(json.dumps({"command": "status", "status": status}, ensure_ascii=False, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: greet, coordinate, status")
        sys.exit(1)


if __name__ == "__main__":
    main()