# Kaniko Debug Steps Implementation Summary

## Overview
I've added comprehensive debugging steps to diagnose Kaniko pod failures across all GitHub Actions workflows that use Kaniko builds. These debug steps trigger automatically when Kaniko build steps fail (`if: failure()`) and provide detailed diagnostics to help identify the root cause of build failures.

## Workflows Updated

### 1. `.github/workflows/pr-checks.yml`
**Debug Steps Added:**
- 🔍 Debug Backend Kaniko Build Failure (after backend build)
- 🔍 Debug Frontend Kaniko Build Failure (after frontend build)

**Job Names Monitored:**
- `backend-build-pr-${{ github.event.pull_request.number }}`
- `frontend-build-pr-${{ github.event.pull_request.number }}`

### 2. `.github/workflows/ci-k3s.yml`
**Debug Steps Added:**
- 🔍 Debug Backend Kaniko Build Failure (after backend build)
- 🔍 Debug Frontend Kaniko Build Failure (after frontend build) 
- 🔍 Debug Trivy Security Scan Failure (after Trivy scan)

**Job Names Monitored:**
- `backend-build-${{ github.run_id }}`
- `frontend-build-${{ github.run_id }}`
- `trivy-scan-${{ github.run_id }}`

### 3. `.github/workflows/frontend-v2-pr.yml`
**Debug Steps Added:**
- 🔍 Debug Frontend Kaniko Build Failure (after frontend container build)

**Job Names Monitored:**
- `kaniko-frontend-${{ github.run_id }}`

### 4. `.github/workflows/ci.yml`
**Debug Steps Added:**
- 🔍 Debug Kaniko Test Container Build Failure (after optimized test container build)

**Job Names Monitored:**
- `kaniko-build-${{ github.run_id }}`

## Debug Features

### 1. Pod Discovery
- **Method 1:** Find by `job-name` label (primary method)
- **Method 2:** Find by `app=kaniko-build` label with additional filters
- **Method 3:** Fallback pattern matching for pods
- **Fallback:** Direct job log access when no pod is found

### 2. Comprehensive Diagnostics

#### Job Status and Events
- Job description and status
- Job-level events and conditions
- Available jobs listing when target job not found

#### Pod Diagnostics (when pod exists)
- Complete pod description
- Pod status and phase information
- Pod-level events and state changes
- Resource assignment and scheduling info

#### Container Logs
- **Init Container Logs:** `prepare-build-context`, `prepare-dockerfile`
- **Kaniko Container Logs:** Main executor logs with fallback to all containers
- **Job Logs:** Direct job log access as fallback
- **Log Limits:** Last 50-100 lines for readability

#### Resource Status
- ConfigMaps related to build (Dockerfile, context)
- Namespace resource overview
- Resource quotas and limits
- Recent pods, jobs, and configmaps

### 3. Build-Specific Analysis

#### Backend Builds
- Git clone verification
- Dockerfile ConfigMap status
- Base image accessibility
- Resource constraint analysis

#### Frontend Builds
- Node.js build process diagnostics
- Multi-stage Docker build analysis
- Build context tarball verification
- nginx configuration checks
- Memory-intensive build warnings

#### Test Container Builds
- Dockerfile creation fallback logic
- Git context access verification
- Permission check integration
- Test dependency installation issues

#### Security Scans (Trivy)
- Trivy container execution status
- Base image scanning results
- Security scan timeout analysis

### 4. Troubleshooting Guidance

Each debug step provides specific troubleshooting hints:
- **Common failure patterns** and their causes
- **Resource constraint** indicators
- **Network connectivity** issues
- **Permission problems** identification
- **Next debugging steps** suggestions

## Key Benefits

### 1. **Automated Trigger**
- Debug steps only run on failure (`if: failure()`)
- No performance impact on successful builds
- Immediate diagnosis without manual intervention

### 2. **Pod Discovery Resilience**
- Multiple methods to find Kaniko pods
- Handles edge cases where pods don't exist
- Works across different Kubernetes configurations

### 3. **Comprehensive Coverage**
- All container logs (init + main containers)
- Job and pod events
- Resource status and quotas
- ConfigMap verification

### 4. **Clear Output Format**
- Structured sections with clear headers
- Emoji indicators for status (✅❌⚠️🔍)
- Readable error messages
- Action-oriented troubleshooting hints

### 5. **Context-Aware Analysis**
- Workflow-specific job naming
- Build-type-specific diagnostics
- Environment-aware namespace handling
- PR-specific vs run-specific identifiers

## Usage

When a Kaniko build fails, the debug step will automatically:

1. **Discover** the failed Kaniko pod using job selectors
2. **Collect** comprehensive diagnostic information
3. **Display** structured analysis in GitHub Actions logs
4. **Provide** specific troubleshooting guidance
5. **Suggest** next steps for resolution

## Template for Future Use

A reusable debug template is available at:
`.github/debug-kaniko-template.yml`

This can be customized and added to new workflows that use Kaniko builds.

## Example Output Structure

```
🔍 =====================================
🔍 KANIKO BUILD FAILURE DIAGNOSTICS
🔍 =====================================

🔍 Job Name: backend-build-pr-123
🔍 Namespace: github-runner
🔍 Build Type: backend

📋 Step 1: Finding Kaniko pod...
✅ Found pod by job-name label: backend-build-pr-123-xyz

📋 Step 2: Job Status and Events
🔍 Job description: [detailed job info]
🔍 Job events: [relevant events]

📋 Step 3: Pod Diagnostics
🔍 Pod description: [pod status details]
🔍 Pod events: [pod-level events]

📋 Step 4: Container Logs
🔍 Init container logs: [prepare-build-context logs]
🔍 Kaniko container logs: [main executor logs]

📋 Step 5: Resource Status
🔍 ConfigMaps: [build-related resources]
🔍 Namespace overview: [recent resources]

🔧 Troubleshooting suggestions: [specific guidance]

🔍 ===============================
🔍 END KANIKO FAILURE ANALYSIS
🔍 ===============================
```

This implementation provides a robust debugging foundation for diagnosing Kaniko pod failures and should significantly reduce the time needed to identify and resolve build issues.