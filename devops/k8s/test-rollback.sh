#!/bin/bash
#
# Rollback operations test through WireGuard tunnel
# This test verifies rollback capabilities
#

set -e

# Configuration
NAMESPACE="${NAMESPACE:-speacher}"
SERVER_WG_IP="${SERVER_WG_IP:-10.0.0.1}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-backend}"

echo "🔄 Rollback Operations Test Suite"
echo "================================"
echo "Namespace: $NAMESPACE"
echo "Deployment: $DEPLOYMENT_NAME"
echo "Server: $SERVER_WG_IP"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" = "pass" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        [ -n "$message" ] && echo "  $message"
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        [ -n "$message" ] && echo "  $message"
    fi
}

echo ""
echo "Phase 1: Pre-test Setup"
echo "================================"

echo ""
echo "Test 1: Create Test Deployment"
echo "------------------------------------"

# Create test namespace
kubectl create namespace "$NAMESPACE-rollback-test" &>/dev/null || true

# Create initial deployment
cat <<EOF | kubectl apply -n "$NAMESPACE-rollback-test" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: "$DEPLOYMENT_NAME"
  labels:
    app: test-rollback
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-rollback
  template:
    metadata:
      labels:
        app: test-rollback
        version: "v1"
    spec:
      containers:
      - name: nginx
        image: nginx:1.21-alpine
        ports:
        - containerPort: 80
EOF

# Wait for deployment
kubectl wait --for=condition=available deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null

if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" &>/dev/null; then
    REPLICAS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.replicas}')
    test_result "Initial deployment created" "pass" "$REPLICAS replicas"
else
    test_result "Initial deployment created" "fail" "Deployment not found"
    exit 1
fi

echo ""
echo "Phase 2: Rollback History"
echo "================================"

echo ""
echo "Test 2: Check Rollback History"
echo "------------------------------------"

# Update deployment to create revision
cat <<EOF | kubectl apply -n "$NAMESPACE-rollback-test" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: "$DEPLOYMENT_NAME"
  labels:
    app: test-rollback
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-rollback
  template:
    metadata:
      labels:
        app: test-rollback
        version: "v2"
    spec:
      containers:
      - name: nginx
        image: nginx:1.22-alpine
        ports:
        - containerPort: 80
EOF

# Wait for rollout
kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null

# Check revision history
REVISION_HISTORY=$(kubectl rollout history deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" 2>/dev/null)

if [ -n "$REVISION_HISTORY" ]; then
    REVISION_COUNT=$(echo "$REVISION_HISTORY" | grep -c "REVISION" || echo "0")
    test_result "Rollup history available" "pass" "$REVISION_COUNT revision(s) tracked"

    # Show history
    echo ""
    echo "  Revision History:"
    echo "$REVISION_HISTORY" | sed 's/^/    /'
else
    test_result "Rollup history available" "fail" "No history found"
fi

echo ""
echo "Phase 3: Rollback Operations"
echo "================================"

echo ""
echo "Test 3: Rollback to Previous Version"
echo "------------------------------------"

# Perform rollback
kubectl rollout undo deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" &>/dev/null

# Wait for rollback
if kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null; then
    test_result "Can rollback to previous revision" "pass"

    # Verify image changed back
    CURRENT_IMAGE=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.template.spec.containers[0].image}')
    if [[ "$CURRENT_IMAGE" == *"1.21"* ]]; then
        test_result "Rollback restored correct image" "pass" "Image: $CURRENT_IMAGE"
    else
        test_result "Rollback restored correct image" "fail" "Image: $CURRENT_IMAGE (expected nginx:1.21-alpine)"
    fi
else
    test_result "Can rollback to previous revision" "fail" "Rollout status failed"
fi

echo ""
echo "Test 4: Rollback to Specific Revision"
echo "------------------------------------"

# Create another revision
cat <<EOF | kubectl apply -n "$NAMESPACE-rollback-test" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: "$DEPLOYMENT_NAME"
  labels:
    app: test-rollback
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-rollback
  template:
    metadata:
      labels:
        app: test-rollback
        version: "v3"
    spec:
      containers:
      - name: nginx
        image: nginx:1.23-alpine
        ports:
        - containerPort: 80
EOF

kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null

# Rollback to specific revision (to revision 1)
kubectl rollout undo deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --to-revision=1 &>/dev/null

# Wait for rollback
if kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null; then
    test_result "Can rollback to specific revision" "pass" "Rolled back to revision 1"

    CURRENT_IMAGE=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.template.spec.containers[0].image}')
    if [[ "$CURRENT_IMAGE" == *"1.21"* ]]; then
        test_result "Specific revision rollback successful" "pass" "Restored image: $CURRENT_IMAGE"
    else
        test_result "Specific revision rollback successful" "fail" "Image: $CURRENT_IMAGE"
    fi
else
    test_result "Can rollback to specific revision" "fail" "Rollback command failed"
fi

echo ""
echo "Phase 4: Rollback Pause/Resume"
echo "================================"

echo ""
echo "Test 5: Pause Rollout"
echo "------------------------------------"

# Pause rollout
kubectl rollout pause deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" &>/dev/null

PAUSED_CONDITION=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.paused}')
if [ "$PAUSED_CONDITION" = "true" ]; then
    test_result "Can pause deployment rollout" "pass" "Rollout paused"
else
    test_result "Can pause deployment rollout" "fail" "Pause not effective"
fi

echo ""
echo "Test 6: Resume Rollout"
echo "------------------------------------"

# Resume rollout
kubectl rollout resume deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" &>/dev/null

PAUSED_CONDITION=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.paused}')
if [ "$PAUSED_CONDITION" = "false" ]; then
    test_result "Can resume deployment rollout" "pass" "Rollout resumed"
else
    test_result "Can resume deployment rollout" "fail" "Still paused"
fi

echo ""
echo "Phase 5: Scale Operations"
echo "================================"

echo ""
echo "Test 7: Scale Up Deployment"
echo "------------------------------------"

# Scale up
kubectl scale deployment/"$DEPLOYMENT_NAME" --replicas=3 -n "$NAMESPACE-rollback-test" &>/dev/null

sleep 5

REPLICAS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.replicas}')
READY_REPLICAS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.status.readyReplicas}')

if [ "$REPLICAS" -eq 3 ]; then
    test_result "Can scale deployment up" "pass" "Requested: 3, Ready: $READY_REPLICAS"
else
    test_result "Can scale deployment up" "fail" "Expected 3 replicas, got $REPLICAS"
fi

echo ""
echo "Test 8: Scale Down Deployment"
echo "------------------------------------"

# Scale down
kubectl scale deployment/"$DEPLOYMENT_NAME" --replicas=1 -n "$NAMESPACE-rollback-test" &>/dev/null

sleep 5

REPLICAS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.spec.replicas}')
READY_REPLICAS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE-rollback-test" -o jsonpath='{.status.readyReplicas}')

if [ "$REPLICAS" -eq 1 ]; then
    test_result "Can scale deployment down" "pass" "Requested: 1, Ready: $READY_REPLICAS"
else
    test_result "Can scale deployment down" "fail" "Expected 1 replica, got $REPLICAS"
fi

echo ""
echo "Test 9: Pod Status During Scale"
echo "------------------------------------"

# Check pod count
POD_COUNT=$(kubectl get pods -n "$NAMESPACE-rollback-test" -l app=test-rollback --no-headers | wc -l)

if [ "$POD_COUNT" -eq 1 ]; then
    test_result "Pod count matches replicas" "pass" "$POD_COUNT pod(s) running"
else
    test_result "Pod count matches replicas" "fail" "Expected 1 pod, found $POD_COUNT"
fi

echo ""
echo "Phase 6: Cleanup"
echo "================================"

echo ""
echo "Test 10: Cleanup Test Resources"
echo "------------------------------------"

# Delete test namespace
kubectl delete namespace "$NAMESPACE-rollback-test" --timeout=60s &>/dev/null

# Wait for deletion
for i in {1..12}; do
    if ! kubectl get namespace "$NAMESPACE-rollback-test" &>/dev/null; then
        break
    fi
    echo "  Waiting for namespace deletion... ($i/12)"
    sleep 5
done

if ! kubectl get namespace "$NAMESPACE-rollback-test" &>/dev/null; then
    test_result "Can cleanup test resources" "pass" "All resources deleted"
else
    test_result "Can cleanup test resources" "fail" "Namespace still exists"
fi

echo ""
echo "================================"
echo "Test Results Summary"
echo "================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All rollback tests passed!${NC}"
    exit 0
fi
