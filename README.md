# Multi-Cloud VM Deployment Portal - Cherwell Integration

## Overview

This is a multi-cloud VM deployment portal with integrated Cherwell ticketing system. When VMs are deployed in any cloud provider (GCP, Azure, AWS), the system automatically creates Cherwell incident tickets with child tasks for post-deployment agent installation.

## 🎯 What This Does

### VM Deployment Flow
1. User deploys a VM through the portal (GCP/Azure/AWS)
2. VM is created successfully in the cloud
3. **Cherwell integration automatically triggers**:
   - Creates a parent incident ticket in Cherwell
   - Creates 4 child tasks for agent installation
   - Links tasks to the incident
   - Returns ticket IDs in the deployment response

### Cherwell Tickets Created

After each successful VM deployment, the following is created in Cherwell:

#### Parent Incident
- **Status**: New
- **Service**: Cloud Infrastructure
- **Category**: Request
- **SubCategory**: VM Deployment
- **Description**: Contains VM name, cloud provider, and instance details

#### Child Tasks (Agent Installation)
The system creates 4 tasks linked to the incident:

1. **Tagus Agent Installation** (Linux VMs only)
   - Team: Linux Operations
   - Purpose: Install Tagus monitoring agent

2. **CrowdStrike Agent Installation**
   - Team: Security Operations
   - Purpose: Install CrowdStrike endpoint protection

3. **Tanium Agent Installation**
   - Team: IT Operations
   - Purpose: Install Tanium management agent

4. **SecureWorks Agent Installation**
   - Team: Security Operations
   - Purpose: Install SecureWorks security monitoring

## 🔧 Technical Architecture

### Fixed Circular Import Issue

**Problem**: Cherwell integration was failing with error:
```
WARNING:gcp_backend:Cherwell integration not available - unified_main import failed
```

**Root Cause**: Circular dependency
- `unified_main.py` imports `gcp_backend.py`
- `gcp_backend.py` imports `create_post_deployment_tasks` from `unified_main.py`

**Solution**: Created standalone `cherwell_integration.py` module
```
Before (Circular):
unified_main.py ←→ gcp_backend.py

After (Clean):
unified_main.py → cherwell_integration.py ← gcp_backend.py
```

### Module Structure

```
current-code/
├── backend/
│   ├── cherwell_integration.py    # NEW - All Cherwell API code
│   ├── gcp_backend.py             # Imports from cherwell_integration
│   ├── unified_main.py            # Imports from cherwell_integration
│   ├── azure_ad_auth.py
│   └── gcp_wif.py
├── CHERWELL_CONFIGURATION.md      # Environment variable reference
├── CHERWELL_FIX_SUMMARY.md        # Technical fix details
└── README_CHERWELL_FIX.md         # Quick start guide
```

### Integration Points

Cherwell integration is called after successful VM deployment at:

| Cloud Provider | File | Line | Function |
|---------------|------|------|----------|
| GCP | `gcp_backend.py` | 1267 | `deploy_vm()` |
| AWS | `unified_main.py` | 996, 1021 | `deploy_vm_aws()` |
| Azure | `unified_main.py` | 2005 | `create_vm_async()` |

### Code Flow

```python
# After VM deployment succeeds
create_post_deployment_tasks(vm_name, cloud, vm_details)
    ↓
1. cherwell_get_token()           # Get API token with retry logic
    ↓
2. cherwell_create_incident()     # Create parent incident
    ↓
3. cherwell_create_task() × 4     # Create 4 agent tasks
    ↓
4. send_task_notification_email() # Optional email notification
    ↓
5. Return result with ticket IDs
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# Enable Cherwell integration
CHERWELL_ENABLED=true

# Cherwell API endpoint
CHERWELL_BASE_URL=http://misdsmsapptst01.isd.lacounty.gov/CherwellAPI

# Cherwell API credentials
CHERWELL_CLIENT_GUID=<your-client-guid>
CHERWELL_USER=<your-username>
CHERWELL_PASSWORD=<your-password>
```

### Cherwell Business Object IDs

```bash
# Default values (update if different in your Cherwell instance)
INCIDENT_BUSOBID=6dd53665c0c24cab86870a21cf6434ae
TASK_BUSOBID=9355d5ed41e384ff345b014b6cb1c6e748594aea5b
CUSTOMER_BUSOBID=93405caa107c376a2bd15c4c8885a900be316f3a72
```

### Cherwell Field IDs

Task field IDs (format: `BO:<busObId>,FI:<fieldId>`):

```bash
TASK_FIELD_PARENT_PUBLICID=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9387d7efd191c18d9f954747a08ed7765b883e0925
TASK_FIELD_PARENT_RECID=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9355d6d6f3d7531087eab4456482100476d46ac59b
TASK_FIELD_PARENT_TYPE_NAME=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9387d7edcd90b26af435a5407abac99d264bb2dfcb
TASK_FIELD_SUBJECT=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93ad98a2d68a61778eda3d4d9cbb30acbfd458aea4
TASK_FIELD_NOTES=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9368f144c4290cc902bcf348fba96c062b9b85e8ef
TASK_FIELD_TENANT=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93d663f9eef793e4b2d3934a26b60eb4ab06eb5636
TASK_FIELD_STATUS=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9368f0fb7b744108a666984c21afc932562eb7dc16
TASK_FIELD_OWNED_BY_TEAM=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93cfd5a4e10af4933a573444d08cbc412da491b42e
TASK_FIELD_TASKTYPE=BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9355d5ed6ca15a8308c5e24389b2138b3aa9b6c7fa
```

### Optional Configuration

```bash
# Token retry configuration
CHERWELL_TOKEN_TIMEOUT=30          # Timeout in seconds
CHERWELL_TOKEN_RETRIES=3           # Number of retry attempts
CHERWELL_TOKEN_BACKOFF=1.5         # Exponential backoff factor

# Field values
TASK_FIELD_PARENT_TYPE_NAME_VALUE=Incident
TASK_FIELD_TASKTYPE_VALUE=Action
CHERWELL_TENANT_NAME=ISD-ITS

# Email notifications
TASK_NOTIFICATION_EMAIL=email@example.com
SMTP_SERVER=amail.lacounty.gov
SMTP_PORT=25
SMTP_FROM=ecloud@isd.lacounty.gov

# SSL verification
HTTP_VERIFY=true                    # Set to false only for testing
```

## 🚀 Quick Start

### 1. Configure Environment Variables

Copy and edit the environment variables:

```bash
cd current-code
cp .env.template .env
# Edit .env and add Cherwell credentials
```

### 2. Verify Configuration

Check that Cherwell integration is enabled:

```bash
grep CHERWELL .env
```

### 3. Deploy Application

```bash
# Using Docker
docker-compose up -d

# Or directly
cd backend
python -m uvicorn unified_main:app --host 0.0.0.0 --port 8000
```

### 4. Test VM Deployment

Deploy a test VM through the portal and verify:

1. ✅ VM deployment succeeds
2. ✅ Response includes Cherwell ticket data:
```json
{
  "status": "success",
  "vm_name": "test-vm-001",
  "cherwell": {
    "cherwell_enabled": true,
    "incident_id": "INC123456",
    "tasks_created": [
      {"subject": "Install Tagus Agent (Linux)", "task_id": "TSK123"},
      {"subject": "Install CrowdStrike Agent", "task_id": "TSK124"},
      {"subject": "Install Tanium Agent (Claude)", "task_id": "TSK125"},
      {"subject": "Install SecureWorks Agent (Jeff Page)", "task_id": "TSK126"}
    ]
  }
}
```

3. ✅ Check Cherwell UI for created incident and tasks

## 🔍 Verification

### Check Application Logs

Look for these log messages (NO warnings):

```
✅ INFO:cherwell_integration:Cherwell token acquired successfully
✅ INFO:cherwell_integration:Cherwell incident created: INC123456
✅ INFO:cherwell_integration:Cherwell task created: TSK123
✅ INFO:cherwell_integration:Created 4 tasks for VM test-vm-001 in Cherwell
```

**NOT this** (old error):
```
❌ WARNING:gcp_backend:Cherwell integration not available - unified_main import failed
```

### Check CHERWELL_INTEGRATION_AVAILABLE

In Python shell:
```python
import sys
sys.path.insert(0, 'backend')
from gcp_backend import CHERWELL_INTEGRATION_AVAILABLE
print(CHERWELL_INTEGRATION_AVAILABLE)  # Should be True
```

## 🛠️ Troubleshooting

### Issue: "Cherwell integration not available" warning

**Cause**: Import error (fixed in this PR)

**Solution**: Ensure `cherwell_integration.py` exists in backend directory

### Issue: No Cherwell tickets created

**Diagnosis**:
1. Check `CHERWELL_ENABLED=true` is set
2. Verify credentials are correct
3. Check network connectivity to Cherwell server
4. Review application logs for errors

**Common causes**:
- `CHERWELL_ENABLED=false` (default)
- Missing or incorrect credentials
- Network/firewall blocking Cherwell server
- DNS cannot resolve Cherwell hostname

### Issue: DNS resolution error for Cherwell server

**Error**: `Failed to resolve 'misdsmsapptst01.isd.lacounty.gov'`

**Cause**: Network/DNS issue (not a code issue)

**Solution**:
1. Verify hostname resolves: `nslookup misdsmsapptst01.isd.lacounty.gov`
2. Check network connectivity from deployment environment
3. Verify firewall rules allow access to Cherwell server
4. Contact network team if needed

**Note**: This is a non-blocking error - VM deployment will succeed even if Cherwell is unreachable.

### Issue: Token authentication failed

**Error**: `Failed to get Cherwell token`

**Solution**:
1. Verify `CHERWELL_CLIENT_GUID` is correct
2. Verify `CHERWELL_USER` and `CHERWELL_PASSWORD` are correct
3. Check user has API access in Cherwell
4. Verify `CHERWELL_BASE_URL` is correct

## 📊 Deployment Response Examples

### Successful Deployment with Cherwell

```json
{
  "status": "success",
  "vm_name": "prod-web-server-001",
  "cloud": "gcp",
  "project": "my-project-123",
  "zone": "us-central1-a",
  "machine_type": "e2-medium",
  "instance_id": "1234567890123456789",
  "cherwell": {
    "cherwell_enabled": true,
    "incident_id": "INC789012",
    "tasks_created": [
      {
        "subject": "Install Tagus Agent (Linux)",
        "task_id": "TSK789013"
      },
      {
        "subject": "Install CrowdStrike Agent (Linux)",
        "task_id": "TSK789014"
      },
      {
        "subject": "Install Tanium Agent (Claude) - Linux",
        "task_id": "TSK789015"
      },
      {
        "subject": "Install SecureWorks Agent (Jeff Page) - Linux",
        "task_id": "TSK789016"
      }
    ]
  }
}
```

### Deployment when Cherwell is Disabled

```json
{
  "status": "success",
  "vm_name": "test-vm-001",
  "cherwell": {
    "cherwell_enabled": false
  }
}
```

### Deployment when Cherwell Fails (Non-blocking)

```json
{
  "status": "success",
  "vm_name": "prod-vm-001",
  "cherwell": {
    "cherwell_enabled": true,
    "error": "Failed to get Cherwell token"
  }
}
```

## 🔒 Security Notes

1. **Never commit credentials** - Use environment variables or secrets management
2. **Set HTTP_VERIFY=true in production** - SSL verification should be enabled
3. **Use secure token storage** - Rotate API credentials regularly
4. **Limit API user permissions** - Grant minimum required access
5. **Monitor API usage** - Track Cherwell API calls for anomalies

## 📚 Additional Documentation

- **[CHERWELL_CONFIGURATION.md](./CHERWELL_CONFIGURATION.md)** - Complete environment variable reference
- **[CHERWELL_FIX_SUMMARY.md](./CHERWELL_FIX_SUMMARY.md)** - Technical details of the circular import fix
- **[README_CHERWELL_FIX.md](./README_CHERWELL_FIX.md)** - Quick start guide for the fix

## 🔄 How It Compares to cherwell/multi-cloud-subscription-portal-main

| Feature | cherwell/multi-cloud-subscription-portal-main | current-code (This Implementation) |
|---------|---------------------------------------------|-----------------------------------|
| **Purpose** | Subscription request management | VM deployment automation |
| **Cherwell Tickets** | CIDR Approval, VNet Creation, Storage | Agent Installation (Tagus, CrowdStrike, etc) |
| **API Pattern** | ✅ Same (token → incident → tasks) | ✅ Same (token → incident → tasks) |
| **Authorization** | ✅ Bearer token | ✅ Bearer token |
| **Error Handling** | ✅ Non-blocking with retry | ✅ Non-blocking with retry |
| **Module Structure** | Single main.py | ✅ Modular (cherwell_integration.py) |

**Both use the same Cherwell API integration pattern** - only the business logic differs based on their specific use cases.

## 🎯 Success Criteria

After deployment, verify:

- [x] No circular import warnings in logs
- [x] `CHERWELL_INTEGRATION_AVAILABLE = True`
- [x] VM deployments succeed (GCP/Azure/AWS)
- [x] Cherwell incident created with correct details
- [x] 4 agent installation tasks created
- [x] Tasks linked to parent incident
- [x] Ticket IDs returned in deployment response
- [x] Email notification sent (if configured)
- [x] Integration is non-blocking (VM succeeds even if Cherwell fails)

## 🤝 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review application logs for error messages
3. Verify environment variables are set correctly
4. Check network connectivity to Cherwell server
5. Contact the DevOps team for assistance

## 📝 Changelog

### [2026-02-12] - Cherwell Integration Fix
- **Fixed**: Circular import preventing Cherwell integration from loading
- **Added**: Standalone `cherwell_integration.py` module
- **Changed**: Import structure to eliminate circular dependency
- **Result**: `CHERWELL_INTEGRATION_AVAILABLE` now correctly set to `True`
- **Commits**: d6bef20 (main fix), 05b1663 (code review fixes)

---

**Status**: ✅ Ready for Production
**Version**: 1.0
**Last Updated**: 2026-02-12
