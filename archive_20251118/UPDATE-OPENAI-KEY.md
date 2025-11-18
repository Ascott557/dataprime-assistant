# Update OpenAI API Key - Quick Guide

## The Issue

Your AI recommendations are failing with:
```
Error code: 401 - Incorrect API key provided
```

## The Fix (3 Simple Steps)

### Step 1: Get Your OpenAI API Key

1. Visit: https://platform.openai.com/account/api-keys
2. Log in to your OpenAI account
3. Click "**+ Create new secret key**"
4. Give it a name (e.g., "ecommerce-demo")
5. Copy the key (starts with `sk-proj-...` or `sk-...`)

⚠️ **Important**: Copy the key immediately - you won't be able to see it again!

### Step 2: Update the Kubernetes Secret

Run these commands from your local machine:

```bash
# SSH to your EC2 instance
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Once connected, update the OpenAI API key
# Replace YOUR_ACTUAL_OPENAI_KEY with the key you copied
kubectl patch secret dataprime-secrets -n dataprime-demo \
  -p="{\"data\":{\"OPENAI_API_KEY\":\"$(echo -n 'YOUR_ACTUAL_OPENAI_KEY' | base64)\"}}"

# You should see:
# secret/dataprime-secrets patched
```

### Step 3: Restart the AI Service

```bash
# Still on the EC2 instance, restart the Recommendation AI service
kubectl rollout restart deployment/recommendation-ai -n dataprime-demo

# Wait for the pod to be ready (should take ~20 seconds)
kubectl get pods -n dataprime-demo -l app=recommendation-ai -w

# Press Ctrl+C once you see the new pod Running with 1/1 Ready
```

### Step 4: Test It

1. Open your browser: http://54.235.171.176:30020
2. Enter a search query: "laptop for gaming"
3. Click "**Get AI Recommendations**"
4. You should now see AI-generated product recommendations! 🎉

---

## Alternative: Test from Command Line

If you want to test the fix before trying in the browser:

```bash
# Still on EC2, run this test
kubectl run -n dataprime-demo test-ai --image=curlimages/curl:latest --rm -i --restart=Never -- \
  curl -s -X POST http://api-gateway:8010/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","user_context":"laptop for gaming"}' \
  --max-time 30

# Should return JSON with recommendations (not an error)
```

---

## Troubleshooting

### "Still getting 401 error"

Check that the key was updated correctly:

```bash
# Verify the secret contains the new key
kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
echo ""  # Add newline

# Should print your API key (starts with sk-...)
```

Make sure you restarted the deployment:

```bash
# Check pod age - should be recent (< 5 minutes)
kubectl get pods -n dataprime-demo -l app=recommendation-ai

# If the pod is old, restart again
kubectl rollout restart deployment/recommendation-ai -n dataprime-demo
```

### "Pod is not starting"

Check pod logs for errors:

```bash
kubectl logs -n dataprime-demo deployment/recommendation-ai --tail=50
```

### "OpenAI API key is valid but still getting errors"

You might have rate limits or billing issues with OpenAI:

1. Check your OpenAI account: https://platform.openai.com/account/usage
2. Verify you have credits/billing set up
3. Check if the model (gpt-4-turbo) is available in your account

---

## Without OpenAI API Key? Use Mock Mode

If you don't have an OpenAI API key but want to test the application, you can enable mock mode:

```bash
# Set environment variable to use mock responses
kubectl set env deployment/recommendation-ai -n dataprime-demo USE_MOCK_AI=true
kubectl rollout restart deployment/recommendation-ai -n dataprime-demo
```

**Note**: This will return sample/fake recommendations instead of real AI-generated ones. Useful for demos and testing telemetry without OpenAI costs.

---

## Quick Reference Commands

```bash
# SSH to EC2
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Update OpenAI key (replace YOUR_KEY)
kubectl patch secret dataprime-secrets -n dataprime-demo \
  -p="{\"data\":{\"OPENAI_API_KEY\":\"$(echo -n 'YOUR_KEY' | base64)\"}}"

# Restart AI service
kubectl rollout restart deployment/recommendation-ai -n dataprime-demo

# Watch pod status
kubectl get pods -n dataprime-demo -l app=recommendation-ai -w

# Test from command line
kubectl run -n dataprime-demo test-ai --image=curlimages/curl:latest --rm -i --restart=Never -- \
  curl -s -X POST http://api-gateway:8010/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","user_context":"laptop for gaming"}' \
  --max-time 30
```

---

## After Successful Update

Once you've updated the API key and tested successfully:

1. ✅ **RUM tracking** should be working
2. ✅ **AI recommendations** should be generating
3. ✅ **Full telemetry** should flow to Coralogix:
   - Frontend RUM data
   - API Gateway traces
   - Recommendation AI traces (including OpenAI spans)
   - Database calls
   - Infrastructure metrics

### Verify in Coralogix:

1. **RUM Dashboard**: https://coralogix.com/rum
   - Application: `ecom_reccomendation`
   - Should see sessions, actions, performance metrics

2. **APM/Traces**: Navigate to APM
   - Application: `ecommerce-recommendation`
   - Should see full request traces from frontend → API Gateway → Recommendation AI → OpenAI

3. **AI Center**: Check AI-specific traces
   - Should see OpenAI calls with tool invocations
   - Database spans from product lookups

---

**Expected Time**: 5 minutes  
**Difficulty**: Easy  
**Cost**: OpenAI API usage (typically $0.01-0.10 per recommendation request)

