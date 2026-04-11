"""
Compass NYC — Terminal Chat Interface
────────────────────────────────────────────────────────────
Interactive terminal chat with the conversational agent.
Supports multi-benefit detection and streaming responses.
"""

import sys
from conversational_agent import ConversationalAgent
from config import BENEFITS


def print_banner():
    """Print welcome banner."""
    print("\n" + "═"*70)
    print("  COMPASS NYC — Terminal Chat")
    print("═"*70)
    print("  Chat with Compass to find NYC social services.")
    print(f"  Available benefits: {len(BENEFITS)}")
    print("─"*70)
    print("  Commands:")
    print("    /new     - Start a new conversation")
    print("    /history - Show conversation history")
    print("    /benefits - List available benefits")
    print("    /help    - Show this help message")
    print("    /quit    - Exit")
    print("═"*70 + "\n")


def print_help():
    """Print help message."""
    print("\n" + "─"*70)
    print("  COMMANDS:")
    print("─"*70)
    print("  /new       Start a new conversation (clears history)")
    print("  /history   Show all messages in current conversation")
    print("  /benefits  List all available benefits")
    print("  /help      Show this help message")
    print("  /quit      Exit the chat")
    print("─"*70)
    print("\n  TIPS:")
    print("  • Just type naturally - the system auto-detects relevant benefits")
    print("  • Ask follow-up questions - it remembers your conversation")
    print("  • Mention your borough for location filtering")
    print("─"*70 + "\n")


def print_benefits():
    """Print available benefits."""
    print("\n" + "─"*70)
    print("  AVAILABLE BENEFITS:")
    print("─"*70)
    for benefit_id, config in BENEFITS.items():
        print(f"  • {config['name']}")
        print(f"    {config['description']}")
        print(f"    Category: {config['category']}")
        print()
    print("─"*70 + "\n")


def print_history(agent):
    """Print conversation history."""
    history = agent.get_history()
    
    if not history:
        print("\n  (No conversation history yet)\n")
        return
    
    print("\n" + "─"*70)
    print("  CONVERSATION HISTORY:")
    print("─"*70)
    
    for i, msg in enumerate(history, 1):
        role = "YOU" if msg["role"] == "user" else "COMPASS"
        print(f"\n  [{i}] {role}:")
        print(f"  {msg['content']}")
    
    print("─"*70 + "\n")


def format_locations(locations_by_benefit, max_per_benefit=3):
    """Format locations for terminal display."""
    if not locations_by_benefit:
        return ""
    
    output = "\n" + "─"*70 + "\n"
    output += "  SERVICE LOCATIONS:\n"
    output += "─"*70 + "\n"
    
    for benefit_type, locations in locations_by_benefit.items():
        if not locations:
            continue
        
        benefit_name = BENEFITS[benefit_type]["name"]
        output += f"\n  {benefit_name.upper()}\n\n"
        
        for i, loc in enumerate(locations[:max_per_benefit], 1):
            output += f"  {i}. {loc['name']}\n"
            output += f"     📍 {loc['address']}, {loc['borough']} {loc['zip']}\n"
            if loc.get('phone'):
                output += f"     📞 {loc['phone']}\n"
            if loc.get('hours'):
                output += f"     🕐 {loc['hours']}\n"
            output += "\n"
        
        if len(locations) > max_per_benefit:
            output += f"  ... and {len(locations) - max_per_benefit} more locations\n\n"
    
    output += "─"*70 + "\n"
    return output


def main():
    """Main chat loop."""
    print_banner()
    
    # Initialize agent
    agent = ConversationalAgent()
    
    print("  Type your message or /help for commands.\n")
    
    while True:
        try:
            # Get user input
            user_input = input("YOU: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                command = user_input.lower()
                
                if command == '/quit' or command == '/exit':
                    print("\n  Goodbye! Stay safe and healthy. 👋\n")
                    break
                
                elif command == '/new':
                    agent.reset_conversation()
                    print("\n  ✓ Started a new conversation.\n")
                    continue
                
                elif command == '/history':
                    print_history(agent)
                    continue
                
                elif command == '/benefits':
                    print_benefits()
                    continue
                
                elif command == '/help':
                    print_help()
                    continue
                
                else:
                    print(f"\n  Unknown command: {user_input}")
                    print("  Type /help for available commands.\n")
                    continue
            
            # Process user message
            print()  # Blank line before response
            
            # Get response with streaming
            result = agent.chat(user_input)
            
            # Print response (already streamed during generation)
            print()  # Blank line after streaming
            
            # Print locations if any
            if result['locations_by_benefit']:
                print(format_locations(result['locations_by_benefit']))
            
            print()  # Blank line before next prompt
            
        except KeyboardInterrupt:
            print("\n\n  Interrupted. Type /quit to exit or continue chatting.\n")
            continue
        
        except Exception as e:
            print(f"\n  Error: {e}")
            print("  Please try again or type /quit to exit.\n")


if __name__ == "__main__":
    main()