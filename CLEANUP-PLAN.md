# Project Cleanup Plan

## Files to KEEP (Essential)

### Core Application
- `coralogix-dataprime-demo/` - Main application code
- `deployment/` - Kubernetes manifests
- `infrastructure/` - Terraform for AWS
- `scripts/` - Utility scripts
- `docs/` - Documentation directory

### Project Files
- `README.md` - Main project README
- `LICENSE` - Apache 2.0 license
- `NOTICE` - License notice
- `requirements-optimized.txt` - Python dependencies
- `.gitignore` - Git ignore rules

### Final Documentation (Keep 1-2 most recent)
- `FINAL-DEMO-BUTTONS-WORKING.md` - Most recent, comprehensive status
- `test-demo-locally.sh` - Useful testing script

---

## Files to REMOVE (Cleanup)

### Obsolete Tarballs (16 files)
- `app_code_optimized.tar.gz`
- `app_code_update.tar.gz`
- `app_code.tar.gz`
- `app_fixed.tar.gz`
- `app-complete-fix.tar.gz`
- `app.tar.gz`
- `complete-app.tar.gz`
- `db-connection-fix.tar.gz`
- `deployment-update.tar.gz`
- `deployments-fix.tar.gz`
- `final-fix.tar.gz`
- `frontend-demo-fix.tar.gz`
- `https-proxy-fix.tar.gz`
- `k8s_manifests.tar.gz`
- `k8s_optimized.tar.gz`
- `services-update.tar.gz`
- `telemetry_restored.tar.gz`
- `telemetry-fix.tar.gz`

### Intermediate Status/Fix Docs (60+ files)
All the incremental status files can be removed, keeping only the final:
- `ALL-DEMO-BUTTONS-STATUS.md` ❌
- `ARCHITECTURE-SIMPLIFIED.md` ❌
- `AUTOMATION-TELEMETRY-SUMMARY.md` ❌
- `AWS-DEPLOYMENT-GUIDE.md` ❌
- `BUTTON-ISSUE-ANALYSIS.md` ❌
- `COMPLETE-TELEMETRY-STATUS.md` ❌
- `CORALOGIX-DATABASE-MONITORING-FIX.md` ❌
- `CORALOGIX-SETUP.md` ❌
- `CURRENT-STATUS.md` ❌
- `DATABASE-FIXED-COMPLETE.md` ❌
- `DATABASE-MONITORING-QUICK-REF.md` ❌
- `DATABASE-RESTART-TEST-RESULTS.md` ❌
- `DEMO-BUTTONS-FINAL-FIX.md` ❌
- `DEMO-ORCHESTRATION-COMPLETE.md` ❌
- `DEMO-ORCHESTRATION-GUIDE.md` ❌
- `DEMO-READY.md` ❌
- `DEMO-SCENARIOS-QUICK-REF.md` ❌
- `DEMO-SCRIPT-CHEAT-SHEET.md` ❌
- `DEMO-STATUS-FINAL.md` ❌
- `DEPLOYMENT-CHECKLIST.md` ❌
- `DEPLOYMENT-COMPLETE.md` ❌
- `DEPLOYMENT-VERIFICATION.md` ❌
- `DOWNSIZED-DEPLOYMENT-SUCCESS.md` ❌
- `DUPLICATE-CORS-FIX.md` ❌
- `EXECUTE-K3S-MIGRATION.md` ❌
- `FINAL-DEPLOYMENT.md` ❌
- `FINAL-DIAGNOSIS.md` ❌
- `FINAL-SESSION-REPLAY-STATUS.md` ❌
- `FINAL-STATUS-RUM-CDN-ISSUE.md` ❌
- `FINAL-TRACE-VERIFICATION.md` ❌
- `FIX-SUMMARY.md` ❌
- `FRONTEND-DEMO-CORS-FIX.md` ❌
- `HOW-TO-VIEW-COMPLETE-TRACE.md` ❌
- `HTTPS-PROXY-CORS-FIX-FINAL.md` ❌
- `IMAGE-OPTIMIZATION-SUCCESS.md` ❌
- `IMPLEMENTATION-SUMMARY-SCENE-9.md` ❌
- `IMPLEMENTATION-SUMMARY.md` ❌
- `INSTANCE-CRASH-ANALYSIS.md` ❌
- `ISSUE-FIXES.md` ❌
- `ISSUES-RESOLVED-SUMMARY.md` ❌
- `k3s-deployment-log.txt` ❌
- `K3S-MIGRATION-SUMMARY.md` ❌
- `LOAD-GENERATOR-COMPLETE.md` ❌
- `LOAD-GENERATOR-GUIDE.md` ❌
- `MANUAL-INSTRUMENTATION-STATUS.md` ❌
- `MANUAL-SPANS-DEPLOYED.md` ❌
- `MIXED-CONTENT-FIXED.md` ❌
- `MULTI-SERVICE-DATABASE-DEMO.md` ❌
- `MULTI-SERVICE-IMPLEMENTATION-COMPLETE.md` ❌
- `NETWORKING-FIX.md` ❌
- `OPENAI-LLM-TRACEKIT-FIXED.md` ❌
- `OTEL-SEMANTIC-CONVENTIONS-FIX.md` ❌
- `PAKO-COMPRESSION-FIX.md` ❌
- `PHASE-3-AWS-DEPLOYMENT.md` ❌
- `PHASE-3-COMPLETE.md` ❌
- `PHASE1-2-COMPLETE.md` ❌
- `PORT-30444-OPENED.md` ❌
- `POSTGRESQL-IMPLEMENTATION-VERIFIED.md` ❌
- `POSTGRESQL-INSTRUMENTATION-FIX.md` ❌
- `POSTGRESQL-MANUAL-INSTRUMENTATION-COMPLETE.md` ❌
- `POSTGRESQL-SPANS-FIX.md` ❌
- `PROFILING-STATUS-AND-NEXT-STEPS.md` ❌
- `QUICK-START-SCENE-9.5.md` ❌
- `README-ECOMMERCE.md` ❌
- `READY-TO-TEST-FINAL.md` ❌
- `READY-TO-TEST.md` ❌
- `READY-TO-VERIFY-IN-CORALOGIX.md` ❌
- `REINVENT-DEMO-GUIDE.md` ❌
- `REINVENT-DEMO-QUICK-REFERENCE.md` ❌
- `REINVENT-DEMO-READY.md` ❌
- `RUM-APPLICATION-NAME-FIX.md` ❌
- `RUM-DEPLOYMENT-COMPLETE.md` ❌
- `RUM-INTEGRATION.md` ❌
- `RUM-VERIFICATION-STEPS.md` ❌
- `SCENE-9.5-CONTINUOUS-PROFILING.md` ❌
- `SCENE9-FIX-SUMMARY.md` ❌
- `SESSION-REPLAY-ENABLED.md` ❌
- `SPAN-CONTEXT-FIX-DEPLOYED.md` ❌
- `SPAN-CORRELATION-FIXED.md` ❌
- `SQLITE-MIGRATION-SUMMARY.md` ❌
- `SQLITE-SIMPLIFICATION-COMPLETE.md` ❌
- `TELEMETRY-COMPLETE.md` ❌
- `TELEMETRY-FIX-SUMMARY.md` ❌
- `TELEMETRY-FIXES.md` ❌
- `TELEMETRY-INJECTOR-APPROACH.md` ❌
- `TELEMETRY-INVESTIGATION-COMPLETE.md` ❌
- `TELEMETRY-STATUS.md` ❌
- `TELEMETRY-WORKING-SUMMARY.md` ❌
- `TEST-RESULTS.md` ❌
- `TEST-SUCCESS-SUMMARY.md` ❌
- `UPDATE-OPENAI-KEY.md` ❌

### Old Shell Scripts (12 files)
- `build-optimized-image-bg.sh` ❌
- `check-build-status.sh` ❌
- `complete-profiling-setup.sh` ❌
- `complete-scene9.5-setup.sh` ❌
- `DEPLOY-PROFILING.md` ❌
- `DEPLOY-SCENE9-FIX.sh` ❌
- `DEPLOY-TELEMETRY-INJECTOR.sh` ❌
- `final-status.sh` ❌
- `fix-deployment-quick.sh` ❌
- `install-continuous-profiling.sh` ❌
- `quick-status.sh` ❌
- `run-scene9-demo.sh` ❌
- `run-scene9.5-demo.sh` ❌
- `start-ecommerce-demo.sh` ❌
- `test-scene9.sh` ❌

### Test/Debug Files (6 files)
- `check-session-replay.js` ❌
- `compare_trace_extraction.py` ❌
- `deploy-output.log` ❌
- `session-replay-diagnostic.html` ❌
- `test-all-buttons.html` ❌
- `test-frontend.html` ❌

---

## Suggested Action

Create a clean directory structure:

```
dataprime-assistant-1/
├── coralogix-dataprime-demo/    # Main app
├── deployment/                   # K8s manifests
├── infrastructure/               # Terraform
├── scripts/                      # Utilities
├── docs/                         # Documentation
├── README.md                     # Main README
├── FINAL-DEMO-BUTTONS-WORKING.md # Latest status
├── test-demo-locally.sh          # Testing script
├── requirements-optimized.txt    # Dependencies
├── LICENSE
├── NOTICE
└── .gitignore
```

**Total files to remove**: ~95 files (tarballs, intermediate docs, old scripts)
**Total to keep**: ~10-15 essential files + directories

---

## Recommendation

I can execute this cleanup in one command, or we can do it selectively. Would you like me to:

1. **Archive first** (create `archive/` folder with all old files)
2. **Delete immediately** (clean slate)
3. **Selective cleanup** (you tell me what to keep)

Your choice!

