#!/usr/bin/env python3

print("🔍 INVESTIGATING SPAN HIERARCHY ISSUE")
print("="*50)

print("\n📊 UNDERSTANDING THE CORALOGIX TRACE VISUALIZATION:")
print("\nFrom your screenshot, I can see:")
print("- All spans have the SAME trace ID (correct)")  
print("- Spans appear in a connected flow (correct)")
print("- But feedback might appear as separate 'root' visually")

print("\n🤔 POSSIBLE EXPLANATIONS:")

print("\n1️⃣ TIMING ISSUE:")
print("   - Query and feedback happen at different times")
print("   - Coralogix might group them visually as separate 'sessions'")
print("   - Even though they're technically in same trace")

print("\n2️⃣ SPAN RELATIONSHIP ISSUE:")
print("   - Both operations use same parent span ID")
print("   - This creates SIBLING relationship, not parent->child")
print("   - Coralogix visualizes siblings as separate branches")

print("\n3️⃣ SPAN NAMING ISSUE:")
print("   - Operations might have different naming patterns")
print("   - Coralogix groups by operation names")
print("   - Different names = different visual groups")

print("\n4️⃣ ROOT SPAN ISSUE:")
print("   - No explicit 'user session' root span is created")
print("   - First operation becomes root by default")
print("   - Subsequent operations appear as separate roots")

print("\n💡 THE REAL ISSUE:")
print("Looking at trace: 94ac1ac2166371c52329871dfc5c0bce")
print("\nThe issue is likely that there's NO explicit user session root span.")
print("Both query and feedback operations create their own 'root' contexts")
print("even though they share the same trace ID.")

print("\n🔧 SOLUTION NEEDED:")
print("\n1️⃣ FRONTEND: Create explicit user session span")  
print("   - Don't just generate trace/span IDs")
print("   - Actually CREATE a root span in browser")
print("   - All operations become children of this root")

print("\n2️⃣ OR BACKEND: Force hierarchical span creation")
print("   - API Gateway checks if it's first operation in trace")
print("   - If yes, create session root span")  
print("   - If no, make operation child of existing root")

print("\n3️⃣ OR SPAN CHAINING: Use previous operation's span as parent")
print("   - Query operation returns its span ID")
print("   - Feedback uses query span as parent")
print("   - Creates: session -> query -> feedback chain")

print("\n📋 NEXT STEPS:")
print("1. Check if frontend actually creates a browser-side root span")
print("2. Verify if API Gateway handles 'first operation in trace' logic")  
print("3. Test span parent-child relationships with timing")
print("4. Look at actual span IDs in Coralogix for parent relationships")
