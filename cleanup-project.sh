#!/bin/bash
# Project Cleanup Script
# Moves old/intermediate files to an archive directory

set -e

ARCHIVE_DIR="archive_$(date +%Y%m%d)"

echo "=== Project Cleanup ==="
echo "Creating archive directory: $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR"

echo ""
echo "Moving files to archive..."

# Move all .tar.gz files
echo "  - Archiving tarballs..."
find . -maxdepth 1 -name "*.tar.gz" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null || true

# Move intermediate documentation
echo "  - Archiving intermediate docs..."
docs_to_archive=(
    "ALL-DEMO-BUTTONS-STATUS.md"
    "ARCHITECTURE-SIMPLIFIED.md"
    "AUTOMATION-TELEMETRY-SUMMARY.md"
    "AWS-DEPLOYMENT-GUIDE.md"
    "BUTTON-ISSUE-ANALYSIS.md"
    "COMPLETE-TELEMETRY-STATUS.md"
    "CORALOGIX-DATABASE-MONITORING-FIX.md"
    "CORALOGIX-SETUP.md"
    "CURRENT-STATUS.md"
    "DATABASE-FIXED-COMPLETE.md"
    "DATABASE-MONITORING-QUICK-REF.md"
    "DATABASE-RESTART-TEST-RESULTS.md"
    "DEMO-BUTTONS-FINAL-FIX.md"
    "DEMO-ORCHESTRATION-COMPLETE.md"
    "DEMO-ORCHESTRATION-GUIDE.md"
    "DEMO-READY.md"
    "DEMO-SCENARIOS-QUICK-REF.md"
    "DEMO-SCRIPT-CHEAT-SHEET.md"
    "DEMO-STATUS-FINAL.md"
    "DEPLOYMENT-CHECKLIST.md"
    "DEPLOYMENT-COMPLETE.md"
    "DEPLOYMENT-VERIFICATION.md"
    "DOWNSIZED-DEPLOYMENT-SUCCESS.md"
    "DUPLICATE-CORS-FIX.md"
    "EXECUTE-K3S-MIGRATION.md"
    "FINAL-DEPLOYMENT.md"
    "FINAL-DIAGNOSIS.md"
    "FINAL-SESSION-REPLAY-STATUS.md"
    "FINAL-STATUS-RUM-CDN-ISSUE.md"
    "FINAL-TRACE-VERIFICATION.md"
    "FIX-SUMMARY.md"
    "FRONTEND-DEMO-CORS-FIX.md"
    "HOW-TO-VIEW-COMPLETE-TRACE.md"
    "HTTPS-PROXY-CORS-FIX-FINAL.md"
    "IMAGE-OPTIMIZATION-SUCCESS.md"
    "IMPLEMENTATION-SUMMARY-SCENE-9.md"
    "IMPLEMENTATION-SUMMARY.md"
    "INSTANCE-CRASH-ANALYSIS.md"
    "ISSUE-FIXES.md"
    "ISSUES-RESOLVED-SUMMARY.md"
    "K3S-MIGRATION-SUMMARY.md"
    "k3s-deployment-log.txt"
    "LOAD-GENERATOR-COMPLETE.md"
    "LOAD-GENERATOR-GUIDE.md"
    "MANUAL-INSTRUMENTATION-STATUS.md"
    "MANUAL-SPANS-DEPLOYED.md"
    "MIXED-CONTENT-FIXED.md"
    "MULTI-SERVICE-DATABASE-DEMO.md"
    "MULTI-SERVICE-IMPLEMENTATION-COMPLETE.md"
    "NETWORKING-FIX.md"
    "OPENAI-LLM-TRACEKIT-FIXED.md"
    "OTEL-SEMANTIC-CONVENTIONS-FIX.md"
    "PAKO-COMPRESSION-FIX.md"
    "PHASE-3-AWS-DEPLOYMENT.md"
    "PHASE-3-COMPLETE.md"
    "PHASE1-2-COMPLETE.md"
    "PORT-30444-OPENED.md"
    "POSTGRESQL-IMPLEMENTATION-VERIFIED.md"
    "POSTGRESQL-INSTRUMENTATION-FIX.md"
    "POSTGRESQL-MANUAL-INSTRUMENTATION-COMPLETE.md"
    "POSTGRESQL-SPANS-FIX.md"
    "PROFILING-STATUS-AND-NEXT-STEPS.md"
    "QUICK-START-SCENE-9.5.md"
    "README-ECOMMERCE.md"
    "READY-TO-TEST-FINAL.md"
    "READY-TO-TEST.md"
    "READY-TO-VERIFY-IN-CORALOGIX.md"
    "REINVENT-DEMO-GUIDE.md"
    "REINVENT-DEMO-QUICK-REFERENCE.md"
    "REINVENT-DEMO-READY.md"
    "RUM-APPLICATION-NAME-FIX.md"
    "RUM-DEPLOYMENT-COMPLETE.md"
    "RUM-INTEGRATION.md"
    "RUM-VERIFICATION-STEPS.md"
    "SCENE-9.5-CONTINUOUS-PROFILING.md"
    "SCENE9-FIX-SUMMARY.md"
    "SESSION-REPLAY-ENABLED.md"
    "SPAN-CONTEXT-FIX-DEPLOYED.md"
    "SPAN-CORRELATION-FIXED.md"
    "SQLITE-MIGRATION-SUMMARY.md"
    "SQLITE-SIMPLIFICATION-COMPLETE.md"
    "TELEMETRY-COMPLETE.md"
    "TELEMETRY-FIX-SUMMARY.md"
    "TELEMETRY-FIXES.md"
    "TELEMETRY-INJECTOR-APPROACH.md"
    "TELEMETRY-INVESTIGATION-COMPLETE.md"
    "TELEMETRY-STATUS.md"
    "TELEMETRY-WORKING-SUMMARY.md"
    "TEST-RESULTS.md"
    "TEST-SUCCESS-SUMMARY.md"
    "UPDATE-OPENAI-KEY.md"
)

for file in "${docs_to_archive[@]}"; do
    [ -f "$file" ] && mv "$file" "$ARCHIVE_DIR/"
done

# Move old shell scripts
echo "  - Archiving old scripts..."
scripts_to_archive=(
    "build-optimized-image-bg.sh"
    "check-build-status.sh"
    "complete-profiling-setup.sh"
    "complete-scene9.5-setup.sh"
    "DEPLOY-PROFILING.md"
    "DEPLOY-SCENE9-FIX.sh"
    "DEPLOY-TELEMETRY-INJECTOR.sh"
    "final-status.sh"
    "fix-deployment-quick.sh"
    "install-continuous-profiling.sh"
    "quick-status.sh"
    "run-scene9-demo.sh"
    "run-scene9.5-demo.sh"
    "start-ecommerce-demo.sh"
    "test-scene9.sh"
)

for file in "${scripts_to_archive[@]}"; do
    [ -f "$file" ] && mv "$file" "$ARCHIVE_DIR/"
done

# Move test/debug files
echo "  - Archiving test files..."
test_files=(
    "check-session-replay.js"
    "compare_trace_extraction.py"
    "deploy-output.log"
    "session-replay-diagnostic.html"
    "test-all-buttons.html"
    "test-frontend.html"
)

for file in "${test_files[@]}"; do
    [ -f "$file" ] && mv "$file" "$ARCHIVE_DIR/"
done

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Archived files in: $ARCHIVE_DIR/"
echo "  - $(ls -1 $ARCHIVE_DIR | wc -l) files archived"
echo ""
echo "Remaining project structure:"
ls -1 | grep -v "^$ARCHIVE_DIR$" | head -20
echo ""
echo "To permanently delete archived files:"
echo "  rm -rf $ARCHIVE_DIR"
echo ""
echo "To restore a file:"
echo "  mv $ARCHIVE_DIR/filename.md ./"


