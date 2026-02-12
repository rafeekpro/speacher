#!/bin/bash
#
# Full deployment test through WireGuard tunnel
# This test simulates the complete GitHub Actions deployment flow
#

set -e

# Configuration
IMAGE_TAG="${IMAGE_TAG:-test-$(date +%s)}"
NAMESPACE="${NAMESPACE:-speacher}"
SERVER_WG_IP="${SERVER_WG_IP:-10.0.0.1}"

echo "🚀 Full Deployment Test Suite"
echo "================================"
echo "Image Tag: $IMAGE_TAG"
echo "Namespace: $NAMESPACE"
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
echo "Phase 1: Pre-deployment Checks"
echo "================================"

echo ""
echo "Test 1: WireGuard Tunnel Established"
echo "------------------------------------"

# Check tunnel is up
if ip link show wg0 &>/dev/null && ip link show wg0 | grep -q "state UP"; then
    test_result "WireGuard tunnel is active" "pass" "Interface wg0 is UP"
else
    test_result "WireGuard tunnel is active" "fail" "Tunnel not established"
    echo -e "${YELLOW}⚠ Skipping remaining tests - tunnel required${NC}"
    exit 1
fi

echo ""
echo "Test 2: Kubernetes Cluster Access"
echo "------------------------------------"

# Test cluster access
if kubectl get nodes &>/dev/null; then
    NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
    test_result "Can access Kubernetes cluster" "pass" "$NODE_COUNT node(s) available"
else
    test_result "Can access Kubernetes cluster" "fail" "kubectl cannot connect"
    exit 1
fi

echo ""
echo "Test 3: Namespace Management"
echo "------------------------------------"

# Test namespace creation/deletion
kubectl create namespace "$NAMESPACE-test" &>/dev/null || true

if kubectl get namespace "$NAMESPACE-test" &>/dev/null; then
    test_result "Can create Kubernetes namespace" "pass"

    # Cleanup
    kubectl delete namespace "$NAMESPACE-test" --timeout=60s &>/dev/null
    if ! kubectl get namespace "$NAMESPACE-test" &>/dev/null; then
        test_result "Can delete Kubernetes namespace" "pass"
    else
        test_result "Can delete Kubernetes namespace" "fail" "Namespace still exists"
    fi
else
    test_result "Can create Kubernetes namespace" "fail" "Permission denied"
fi

echo ""
echo "Phase 2: Image Operations"
echo "================================"

echo ""
echo "Test 4: Image Loading Simulation"
echo "------------------------------------"

# Simulate image operations (in real deployment, images are loaded from tar)
if command -v k3s &>/dev/null; then
    # Check if we can query k3s containerd images
    if k3s ctr images ls &>/dev/null; then
        IMAGE_COUNT=$(k3s ctr images ls --no-headers | wc -l)
        test_result "Can query containerd images" "pass" "$IMAGE_COUNT images in storage"
    else
        test_result "Can query containerd images" "fail" "k3s ctr unavailable"
    fi
elif command -v ctr &>/dev/null; then
    if ctr images ls &>/dev/null; then
        test_result "Can query containerd images" "pass"
    else
        test_result "Can query containerd images" "fail" "ctr command failed"
    fi
else
    echo -e "${YELLOW}⚠ WARNING${NC}: containerd CLI not available, using docker"
    if command -v docker &>/dev/null; then
        if docker images &>/dev/null; then
            test_result "Can query docker images" "pass"
        else
            test_result "Can query docker images" "fail"
        fi
    fi
fi

echo ""
echo "Phase 3: Manifest Deployment"
echo "================================"

echo ""
echo "Test 5: Apply Manifests"
echo "------------------------------------"

# Create test namespace
kubectl create namespace "$NAMESPACE-test" &>/dev/null || true

# Test applying a simple deployment
cat <<EOF | kubectl apply -n "$NAMESPACE-test" -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  test.key: "test-value"
EOF

if kubectl get configmap test-config -n "$NAMESPACE-test" &>/dev/null; then
    test_result "Can apply Kubernetes manifests" "pass" "ConfigMap created"
else
    test_result "Can apply Kubernetes manifests" "fail" "ConfigMap not created"
fi

# Test deployment
cat <<EOF | kubectl apply -n "$NAMESPACE-test" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
  labels:
    app: test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
EOF

# Wait for deployment
kubectl wait --for=condition=available deployment/test-deployment -n "$NAMESPACE-test" --timeout=60s &>/dev/null

if kubectl get deployment test-deployment -n "$NAMESPACE-test" &>/dev/null; then
    READY_REPLICAS=$(kubectl get deployment test-deployment -n "$NAMESPACE-test" -o jsonpath='{.status.readyReplicas}')
    test_result "Can create deployment" "pass" "$READY_REPLICAS replica(s) ready"
else
    test_result "Can create deployment" "fail" "Deployment not created"
fi

echo ""
echo "Phase 4: Rollout Operations"
echo "================================"

echo ""
echo "Test 6: Rollout Status Check"
echo "------------------------------------"

# Test rollout status command
if kubectl rollout status deployment/test-deployment -n "$NAMESPACE-test" --timeout=30s &>/dev/null; then
    test_result "Can check rollout status" "pass" "Rollout command successful"
else
    test_result "Can check rollout status" "fail" "Rollout command timed out"
fi

echo ""
echo "Test 7: Image Update"
echo "------------------------------------"

# Test setting image
kubectl set image deployment/test-deployment nginx=nginx:latest -n "$NAMESPACE-test" &>/dev/null

# Wait for rollout
sleep 5

UPDATED_IMAGE=$(kubectl get deployment/test-deployment -n "$NAMESPACE-test" -o jsonpath='{.spec.template.spec.containers[0].image}')
if [ "$UPDATED_IMAGE" = "nginx:latest" ]; then
    test_result "Can update deployment image" "pass" "Image updated to $UPDATED_IMAGE"
else
    test_result "Can update deployment image" "fail" "Image: $UPDATED_IMAGE"
fi

echo ""
echo "Test 8: Pod Status Check"
echo "------------------------------------"

# Check pod status
POD_NAME=$(kubectl get pods -n "$NAMESPACE-test" -l app=test -o jsonpath='{.items[0].metadata.name}')

if [ -n "$POD_NAME" ]; then
    POD_PHASE=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE-test" -o jsonpath='{.status.phase}')
    if [ "$POD_PHASE" = "Running" ]; then
        test_result "Deployment pods are running" "pass" "Pod $POD_NAME is Running"
    else
        test_result "Deployment pods are running" "fail" "Pod phase: $POD_PHASE"
    fi

    # Test pod logs
    if kubectl logs "$POD_NAME" -n "$NAMESPACE-test" &>/dev/null; then
        test_result "Can retrieve pod logs" "pass"
    else
        test_result "Can retrieve pod logs" "fail"
    fi

    # Test pod execution
    if kubectl exec "$POD_NAME" -n "$NAMESPACE-test" -- ls / &>/dev/null; then
        test_result "Can execute commands in pod" "pass"
    else
        test_result "Can execute commands in pod" "fail"
    fi
else
    test_result "Deployment pods are running" "fail" "No pods found"
fi

echo ""
echo "Test 9: Service Operations"
echo "------------------------------------"

# Create a service
cat <<EOF | kubectl apply -n "$NAMESPACE-test" -f -
apiVersion: v1
kind: Service
metadata:
  name: test-service
spec:
  selector:
    app: test
  ports:
  - port: 80
    targetPort: 80
EOF

if kubectl get service test-service -n "$NAMESPACE-test" &>/dev/null; then
    test_result "Can create service" "pass" "Service test-service created"

    # Get service info
    SERVICE_IP=$(kubectl get service test-service -n "$NAMESPACE-test" -o jsonpath='{.spec.clusterIP}')
    test_result "Service has cluster IP" "pass" "Cluster IP: $SERVICE_IP"
else
    test_result "Can create service" "fail" "Service not created"
fi

echo ""
echo "Phase 5: Cleanup"
echo "================================"

echo ""
echo "Test 10: Resource Cleanup"
echo "------------------------------------"

# Delete test namespace
kubectl delete namespace "$NAMESPACE-test" --timeout=60s &>/dev/null

# Wait for deletion
sleep 5

if ! kubectl get namespace "$NAMESPACE-test" &>/dev/null; then
    test_result "Can cleanup test resources" "pass" "Namespace deleted"
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
    echo -e "${GREEN}✅ All deployment tests passed!${NC}"
    exit 0
fi
