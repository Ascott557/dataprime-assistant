"""Main CLI interface for DataPrime Assistant."""

import sys
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
import typer

from .dataprime_assistant import DataPrimeAssistant
from .utils.instrumentation import initialize_instrumentation
from .utils.genai_instrumentation import initialize_genai_instrumentation

# Initialize Rich console
console = Console()
app = typer.Typer(help="DataPrime Assistant - Convert natural language to DataPrime queries")

def display_welcome():
    """Display welcome message."""
    welcome_text = """
🤖 DataPrime Assistant

Convert natural language to DataPrime queries with AI observability.

Example queries to try:
• "Show me errors from the last hour"
• "Count logs by service"  
• "Find slow API calls yesterday"
• "Top 10 busiest endpoints"
"""
    
    console.print(Panel(welcome_text, title="Welcome", border_style="green"))

def display_result(result: dict):
    """Display query generation result."""
    
    if "error" in result:
        console.print(f"❌ Error: {result['error']}", style="red")
        return
    
    # Display user input
    console.print(f"\n💬 Your input: {result['user_input']}", style="cyan")
    
    # Display intent analysis
    intent = result["intent"]
    intent_text = f"Intent: {intent['type']} (confidence: {intent['confidence']:.2f})"
    if intent['keywords']:
        intent_text += f"\nKeywords: {', '.join(intent['keywords'])}"
    if intent['timeframe']:
        intent_text += f"\nTimeframe: {intent['timeframe']}"
    
    console.print(Panel(intent_text, title="🎯 Intent Analysis", border_style="blue"))
    
    # Display generated query
    query_syntax = Syntax(result["generated_query"], "sql", theme="monokai", line_numbers=False)
    console.print(Panel(query_syntax, title="🔍 Generated DataPrime Query", border_style="green"))
    
    # Display validation results
    validation = result["validation"]
    validation_table = Table(title="Validation Results")
    validation_table.add_column("Metric", style="cyan")
    validation_table.add_column("Value", style="green")
    
    validation_table.add_row("Valid", "✅ Yes" if validation["is_valid"] else "❌ No")
    validation_table.add_row("Syntax Score", f"{validation['syntax_score']:.2f}/1.0")
    validation_table.add_row("Complexity", f"{validation['complexity_score']:.2f}/1.0")
    validation_table.add_row("Est. Cost", validation["estimated_cost"].title())
    
    console.print(validation_table)
    
    # Display issues if any
    if validation["issues"]:
        console.print("\n⚠️ Issues found:", style="yellow")
        for issue in validation["issues"]:
            level_emoji = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
            emoji = level_emoji.get(issue["level"], "•")
            console.print(f"  {emoji} {issue['message']}")
            if issue["suggestion"]:
                console.print(f"    💡 {issue['suggestion']}", style="dim")
    
    # Display performance warnings
    if validation["performance_warnings"]:
        console.print("\n🚀 Performance tips:", style="yellow")
        for warning in validation["performance_warnings"]:
            console.print(f"  • {warning}")
    
    # Display examples used
    if result["examples_used"]:
        console.print(f"\n📚 Examples used ({len(result['examples_used'])}):", style="dim")
        for i, example in enumerate(result["examples_used"], 1):
            console.print(f"  {i}. \"{example['input']}\" → {example['output']}", style="dim")
    
    # Display timing
    console.print(f"\n⏱️ Generated in {result['generation_time']:.3f} seconds", style="dim")

def interactive_mode():
    """Run interactive mode."""
    display_welcome()
    
    try:
        # Initialize instrumentation
        console.print("🔧 Initializing instrumentation...", style="yellow")
        initialize_instrumentation()
        
        # Initialize assistant
        console.print("🤖 Loading DataPrime Assistant...", style="yellow")
        assistant = DataPrimeAssistant()
        
        console.print("✅ Ready! Type your queries or 'quit' to exit.\n", style="green")
        
        while True:
            # Get user input
            user_input = Prompt.ask("\n[cyan]Ask me anything about your logs[/cyan]")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("👋 Goodbye!", style="green")
                break
            
            if user_input.lower() in ['help', 'h']:
                display_welcome()
                continue
            
            # Generate query
            console.print("🔮 Generating DataPrime query...", style="yellow")
            result = assistant.generate_query(user_input)
            
            # Display result
            display_result(result)
            
            # Ask for feedback
            if "generated_query" in result:
                feedback = Prompt.ask(
                    "\n[dim]Rate this result (1-5) or press Enter to skip[/dim]",
                    default=""
                )
                
                if feedback and feedback.isdigit():
                    rating = int(feedback)
                    if 1 <= rating <= 5:
                        comment = Prompt.ask("[dim]Any comments? (optional)[/dim]", default="")
                        assistant.record_feedback(result, rating, comment)
                        console.print("📝 Thank you for your feedback!", style="green")
    
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        sys.exit(1)

@app.command()
def query(
    text: str = typer.Argument(..., help="Natural language query to convert"),
    output_format: str = typer.Option("pretty", help="Output format: pretty, json"),
    explain: bool = typer.Option(False, help="Explain the generated query")
):
    """Generate a single DataPrime query from text."""
    
    try:
        # Initialize instrumentation
        initialize_instrumentation()
        
        # Initialize assistant
        assistant = DataPrimeAssistant()
        
        # Generate query
        result = assistant.generate_query(text)
        
        if output_format == "json":
            console.print(json.dumps(result, indent=2))
        else:
            display_result(result)
            
            if explain and "generated_query" in result:
                console.print("\n🤔 Explaining the query...", style="yellow")
                explanation = assistant.explain_query(result["generated_query"])
                
                if "explanation" in explanation:
                    console.print(Panel(
                        explanation["explanation"], 
                        title="📖 Query Explanation", 
                        border_style="blue"
                    ))
    
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        sys.exit(1)

@app.command()
def validate(query_text: str = typer.Argument(..., help="DataPrime query to validate")):
    """Validate a DataPrime query."""
    
    try:
        # Initialize assistant
        assistant = DataPrimeAssistant()
        
        # Validate query
        validation = assistant._validate_query(query_text)
        
        # Display results
        console.print(f"Query: {query_text}", style="cyan")
        
        validation_table = Table(title="Validation Results")
        validation_table.add_column("Metric", style="cyan")
        validation_table.add_column("Value")
        
        validation_table.add_row(
            "Valid", 
            "✅ Yes" if validation.is_valid else "❌ No"
        )
        validation_table.add_row("Syntax Score", f"{validation.syntax_score:.2f}/1.0")
        validation_table.add_row("Complexity", f"{validation.complexity_score:.2f}/1.0")
        validation_table.add_row("Est. Cost", validation.estimated_cost.title())
        
        console.print(validation_table)
        
        if validation.issues:
            console.print("\nIssues:", style="yellow")
            for issue in validation.issues:
                level_style = {"error": "red", "warning": "yellow", "info": "blue"}
                style = level_style.get(issue.level.value, "white")
                console.print(f"  • [{style}]{issue.message}[/{style}]")
                if issue.suggestion:
                    console.print(f"    💡 {issue.suggestion}", style="dim")
    
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        sys.exit(1)

@app.command()
def examples():
    """Show example queries."""
    
    examples_table = Table(title="Example DataPrime Queries")
    examples_table.add_column("Natural Language", style="cyan", width=40)
    examples_table.add_column("DataPrime Query", style="green", width=50)
    
    sample_examples = [
        ("Show me errors from the last hour", "source logs last 1h | filter $m.severity == 'Error'"),
        ("Count logs by service", "source logs | groupby $l.subsystemname aggregate count()"),
        ("Find slow API calls", "source logs | filter $d.response_time > 1000"),
        ("Top 10 busiest endpoints", "source logs | groupby $d.endpoint aggregate count() | top 10 by count()"),
        ("Show error trends hourly", "source logs last 1d | filter $m.severity == 'Error' | groupby $m.timestamp.roundTime(1h) aggregate count()")
    ]
    
    for nl, dp in sample_examples:
        examples_table.add_row(nl, dp)
    
    console.print(examples_table)

@app.command()
def interactive():
    """Start interactive mode."""
    interactive_mode()

def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # No arguments provided, start interactive mode
        interactive_mode()
    else:
        # Run CLI commands
        app()

if __name__ == "__main__":
    main()