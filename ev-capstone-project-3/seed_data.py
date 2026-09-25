"""
Seed historical customer support data for software products:
- CloudSync Pro
- DataPulse Analytics
- SecureAuth Gateway
- DevFlow CI/CD

Each ticket includes customer query, technical support response, category, and resolution summary.
Embeddings are computed using OpenAIEmbeddings and saved into SQLite.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure the app directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)

# Load env variables from local or parent directory
load_dotenv(os.path.join(CURRENT_DIR, ".env"))
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(os.path.join(PARENT_DIR, "langchain-app", ".env"))

import database
from langchain_openai import OpenAIEmbeddings

HISTORICAL_TICKETS = [
    # ==========================================
    # PRODUCT 1: CloudSync Pro
    # ==========================================
    {
        "ticket_code": "CSP-101",
        "product": "CloudSync Pro",
        "category": "Client Connectivity",
        "customer_query": "My CloudSync Pro desktop client on macOS is permanently stuck on 'Connecting to sync engine...' and never uploads my files.",
        "support_response": (
            "Hi there, thank you for reaching out! On macOS Sonoma and Sequoia, this issue typically occurs when "
            "macOS Local Network or Full Disk Access permissions are revoked or pending approval after an OS update.\n\n"
            "Please follow these troubleshooting steps:\n"
            "1. Quit CloudSync Pro from the menu bar.\n"
            "2. Open macOS System Settings -> Privacy & Security -> Full Disk Access, and ensure CloudSync Pro is toggled ON.\n"
            "3. Under Privacy & Security -> Local Network, ensure CloudSync Pro is permitted.\n"
            "4. Delete the temporary sync lock file if present: run `rm -f ~/Library/Application\\ Support/CloudSyncPro/.sync.lock`.\n"
            "5. Relaunch CloudSync Pro.\n\n"
            "The client will perform a fast 30-second re-hash and resume normal syncing immediately."
        ),
        "resolution_summary": "Resolved by granting Full Disk Access & Local Network permissions in macOS System Settings and clearing `.sync.lock`."
    },
    {
        "ticket_code": "CSP-102",
        "product": "CloudSync Pro",
        "category": "File Conflicts",
        "customer_query": "Two teammates worked on the same budget spreadsheet offline, and now we see duplicate files ending with '(Conflicted Copy 2026-xx-xx)'. How do we resolve this without losing changes?",
        "support_response": (
            "Hello! When two users edit the same binary document (like `.xlsx` or `.docx`) concurrently while disconnected from the cloud, "
            "CloudSync Pro preserves both versions to prevent data loss by designating the later sync as a 'Conflicted Copy'.\n\n"
            "Here is how to resolve it safely:\n"
            "1. Open both the original file and the `(Conflicted Copy)` file side-by-side.\n"
            "2. In Microsoft Excel, navigate to Review -> Compare & Merge Workbooks (or copy over differing cells manually).\n"
            "3. Save the final consolidated version as the primary file.\n"
            "4. Delete the `(Conflicted Copy)` file from your synchronized folder. CloudSync will propagate the deletion.\n"
            "5. Best Practice: In CloudSync Pro Preferences -> Collaboration, enable 'File Lock Notifications' so you are alerted when a teammate has a file open."
        ),
        "resolution_summary": "Explained conflicted copy preservation logic, how to merge Excel sheets, and advised enabling 'File Lock Notifications'."
    },
    {
        "ticket_code": "CSP-103",
        "product": "CloudSync Pro",
        "category": "Performance & Bandwidth",
        "customer_query": "CloudSync Pro is saturating our office internet bandwidth when colleagues sync 50GB design folders. Can we sync over local Wi-Fi instead of downloading from WAN?",
        "support_response": (
            "Hi, great question! Yes, CloudSync Pro features built-in Peer-to-Peer LAN Syncing designed specifically for multi-user office networks.\n\n"
            "To activate LAN Sync:\n"
            "1. In CloudSync Pro Settings -> Bandwidth tab, check 'Enable LAN Sync'.\n"
            "2. Ensure local TCP port 17500 and UDP port 17500 are not blocked by local endpoint firewalls.\n"
            "3. When another team member on the same subnet downloads files already present on your machine, CloudSync transfers data directly over LAN at gigabit speeds without consuming your WAN ISP bandwidth.\n"
            "4. You can also configure bandwidth limits under Settings -> Bandwidth -> Download/Upload Throttling (e.g. limit WAN to 10 MB/s during 9 AM - 6 PM)."
        ),
        "resolution_summary": "Configured LAN Sync on port 17500 and configured scheduled bandwidth throttling to preserve office WAN bandwidth."
    },
    {
        "ticket_code": "CSP-104",
        "product": "CloudSync Pro",
        "category": "Storage & Quotas",
        "customer_query": "I deleted over 100GB of video archives from my CloudSync Pro folder, but my account dashboard still says 'Storage Quota Exceeded (98% full)'. Why hasn't the space freed up?",
        "support_response": (
            "Hello! When you delete files locally, CloudSync Pro retains them in your Cloud Trash and maintains Version History for 30 days (default retention policy) to safeguard against accidental deletions or ransomware.\n\n"
            "To immediately reclaim this quota:\n"
            "1. Log in to the CloudSync Pro Web Portal at `https://cloudsyncpro.internal/portal`.\n"
            "2. Click 'Deleted Files / Trash' on the left navigation bar.\n"
            "3. Select 'Empty Trash' to permanently purge deleted objects.\n"
            "4. If you have large files with multiple past versions, go to Settings -> Storage -> Version Retention, and click 'Purge History older than 7 days'.\n"
            "5. Your storage metrics refresh within 5 minutes."
        ),
        "resolution_summary": "Explained 30-day versioning and Trash retention; instructed customer to empty web portal Trash to release storage quota."
    },
    {
        "ticket_code": "CSP-105",
        "product": "CloudSync Pro",
        "category": "Windows Compatibility",
        "customer_query": "Getting error 'Path too long: Filename exceeds 260 characters' on Windows 11 workstation, preventing our project archive from syncing.",
        "support_response": (
            "Hello! This occurs due to the legacy MAX_PATH 260-character limitation in the default Windows API.\n\n"
            "To enable Windows Native Long Path support:\n"
            "1. Press Win + R, type `gpedit.msc` and press Enter.\n"
            "2. Navigate to: Local Computer Policy -> Computer Configuration -> Administrative Templates -> System -> Filesystem.\n"
            "3. Double-click 'Enable Win32 long paths' and set it to 'Enabled'. Click OK.\n"
            "4. Alternatively, run PowerShell as Administrator: `New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`.\n"
            "5. Restart your workstation and restart CloudSync Pro.\n"
            "Long paths up to 32,767 characters will now synchronize seamlessly."
        ),
        "resolution_summary": "Enabled Windows Win32 LongPathsEnabled in registry and group policy to bypass 260-character path limit."
    },
    {
        "ticket_code": "CSP-106",
        "product": "CloudSync Pro",
        "category": "Security & Encryption",
        "customer_query": "We enabled Zero-Knowledge End-to-End Encryption (E2EE) for our Finance folder, but an employee forgot their passkey. Can your support team reset or recover the encryption key?",
        "support_response": (
            "Hello. Under CloudSync Pro's Zero-Knowledge Architecture, encryption keys are derived client-side on your device using Argon2id and AES-256-GCM. Our servers and support team never receive, store, or have access to your private key.\n\n"
            "Recovery Options:\n"
            "1. Organization Emergency Key: If your Organization Admin configured an Enterprise Master Recovery Certificate during initial E2EE setup, the Admin can recover access via Admin Console -> Security -> Vault Keys -> E2EE Emergency Decryption.\n"
            "2. Device Cache: If the employee is still logged in on an existing trusted secondary machine (e.g. their home laptop or iPad), the cached session key can be used to export a new 24-word recovery phrase under Settings -> Vault Security.\n"
            "3. If neither the passkey nor the recovery certificate exists, data cannot be decrypted by design."
        ),
        "resolution_summary": "Clarified zero-knowledge E2EE policy; guided customer to use Enterprise Master Recovery Certificate or secondary trusted device."
    },
    {
        "ticket_code": "CSP-107",
        "product": "CloudSync Pro",
        "category": "Linux CLI & Headless",
        "customer_query": "How do I run CloudSync Pro as a background systemd daemon on an headless Ubuntu 24.04 LTS server without a graphical desktop?",
        "support_response": (
            "Hi there! CloudSync Pro provides a dedicated headless daemon CLI package `cloudsyncpro-cli`.\n\n"
            "Setup steps:\n"
            "1. Install via apt: `sudo apt update && sudo apt install cloudsyncpro-cli`.\n"
            "2. Authenticate using an API token: `cloudsyncpro-cli login --token YOUR_SERVICE_ACCOUNT_TOKEN`.\n"
            "3. Configure sync path: `cloudsyncpro-cli sync add --remote /Backups --local /var/backups`.\n"
            "4. Enable and start the systemd service:\n"
            "   `sudo systemctl enable --now cloudsyncpro@ubuntu.service`\n"
            "5. Verify daemon status with `cloudsyncpro-cli status`.\n"
            "Logs are streamable via `journalctl -u cloudsyncpro@ubuntu.service -f`."
        ),
        "resolution_summary": "Provided installation and configuration guide for `cloudsyncpro-cli` headless systemd service on Ubuntu."
    },

    # ==========================================
    # PRODUCT 2: DataPulse Analytics
    # ==========================================
    {
        "ticket_code": "DPA-201",
        "product": "DataPulse Analytics",
        "category": "Database Connectors",
        "customer_query": "Connecting DataPulse Analytics to our AWS RDS PostgreSQL database fails with 'SSL error: CERTIFICATE_VERIFY_FAILED: self signed certificate in certificate chain'.",
        "support_response": (
            "Hi! AWS RDS certificates use the Amazon Root CA hierarchy, which requires either supplying the AWS RDS global bundle or specifying SSL root certificates in DataPulse.\n\n"
            "To resolve this in DataPulse Analytics:\n"
            "1. Download the AWS Global Trust Bundle: `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`.\n"
            "2. In DataPulse -> Data Sources -> Edit PostgreSQL Connection:\n"
            "   - Set 'SSL Mode' to `verify-ca` or `verify-full`.\n"
            "   - Upload `global-bundle.pem` into the 'SSL Root Certificate' file input.\n"
            "3. If using an SSH Bastion tunnel, ensure the 'SSH Tunnel' toggle is enabled and test the connection.\n"
            "4. Click 'Test Connection'. It should return 'Connection Successful (PostgreSQL 15/16)'."
        ),
        "resolution_summary": "Uploaded AWS RDS Global CA trust bundle `global-bundle.pem` and configured SSL Mode to `verify-ca`."
    },
    {
        "ticket_code": "DPA-202",
        "product": "DataPulse Analytics",
        "category": "Scheduled Reports",
        "customer_query": "Our scheduled daily Monday executive dashboard PDF export is either not sending emails or arriving with blank charts.",
        "support_response": (
            "Hello! Blank charts in automated PDF generation occur when heavy dashboard widgets (e.g. heatmaps or charts with >50,000 data points) "
            "exceed the default headless Chromium render timeout before charts finish animations.\n\n"
            "To fix this:\n"
            "1. Go to DataPulse -> Dashboards -> Select Executive Dashboard -> Settings -> Export Configuration.\n"
            "2. Increase 'Render Wait Timeout' from the default `5000ms` to `15000ms` (15 seconds).\n"
            "3. Enable 'Wait for Network Idle: 2 connections'.\n"
            "4. Toggle OFF 'Disable Chart Animations on Export' to force charts into their static final state immediately.\n"
            "5. Under 'Email Delivery', verify SMTP credentials or check the Delivery Log under Admin -> Audit -> Email Tasks.\n"
            "Run a manual 'Send Test Export' to confirm complete rendering."
        ),
        "resolution_summary": "Increased headless render timeout to 15s and disabled chart animations in dashboard export configuration."
    },
    {
        "ticket_code": "DPA-203",
        "product": "DataPulse Analytics",
        "category": "Query Performance",
        "customer_query": "A custom SQL query against our snowflake warehouse is timing out with 'Query Execution Timeout: Exceeded limit of 60 seconds'. Can we raise this limit?",
        "support_response": (
            "Hi there! Yes, the default client query timeout is 60 seconds to prevent runaway queries from locking database sessions.\n\n"
            "To adjust the query execution timeout:\n"
            "1. For a single dashboard card: In the SQL Editor, add query hint `-- datapulse:timeout=180` at the very top of your SQL snippet.\n"
            "2. Organization-wide setting: Navigate to Admin Console -> Settings -> Data Sources -> Snowflake -> Advanced -> 'Max Query Timeout (Seconds)', and set it up to `300` (5 minutes).\n"
            "3. Recommended Performance Tip: Check if you can partition by `created_at` date or materialize the aggregate table using DataPulse's 'Scheduled Data Cache / Incremental Sync' feature."
        ),
        "resolution_summary": "Configured query hint `-- datapulse:timeout=180` and updated datasource max query timeout to 300 seconds."
    },
    {
        "ticket_code": "DPA-204",
        "product": "DataPulse Analytics",
        "category": "Real-time Dashboards",
        "customer_query": "Our real-time NOC monitor dashboard stops streaming updates after about 15 minutes of idle display on our office TV wall.",
        "support_response": (
            "Hello! When running dashboards in unattended kiosk / TV mode, browser WebSocket connections are often dropped by intermediary corporate proxies or AWS ALB idle timeouts (default 60s without ping).\n\n"
            "Resolution:\n"
            "1. Enable Kiosk Mode: In the Dashboard URL, append `?mode=kiosk&refresh=30s&keepalive=true`.\n"
            "2. In Admin Settings -> System -> Realtime WebSocket:\n"
            "   - Set 'Heartbeat Ping Interval' to `20s`.\n"
            "   - Enable 'Auto-Reconnect WebSocket with exponential backoff'.\n"
            "3. Ensure the browser machine is configured to disable OS sleep or energy saver."
        ),
        "resolution_summary": "Configured URL parameter `keepalive=true` and enabled 20s WebSocket heartbeat ping to prevent proxy disconnections."
    },
    {
        "ticket_code": "DPA-205",
        "product": "DataPulse Analytics",
        "category": "License Management",
        "customer_query": "Attempting to invite new data analysts, but the system says 'Organization seat quota reached: 25/25 seats active'. Several former employees still occupy seats.",
        "support_response": (
            "Hello! You can easily deprovision inactive users to reclaim seats for your new team members.\n\n"
            "Steps to free up seats:\n"
            "1. Go to Admin Console -> Users & Teams -> Members.\n"
            "2. Filter by 'Status: Active' and sort by 'Last Active Date'.\n"
            "3. For former employees, click the three dots menu (...) -> 'Deactivate User'.\n"
            "   - Note: Do NOT delete the user if they authored existing dashboards; 'Deactivate' reclaims the paid seat while preserving their dashboards and query ownership.\n"
            "4. Your available seat counter will instantly update, allowing you to invite the new analysts."
        ),
        "resolution_summary": "Instructed admin to deactivate dormant users to immediately reclaim seats while preserving dashboard ownership."
    },
    {
        "ticket_code": "DPA-206",
        "product": "DataPulse Analytics",
        "category": "Formulas & Calculations",
        "customer_query": "I am getting unexpected numbers when calculating rolling retention rate using `COUNT_DISTINCT` across sliced date intervals. Why are the totals not matching?",
        "support_response": (
            "Hi there! The reason the numbers don't match simple additions is that `COUNT_DISTINCT(user_id)` is a non-additive metric across dimensions. If a user was active on both Monday and Tuesday, they count once in each daily bucket, but also only once in the weekly aggregate.\n\n"
            "To calculate true cohort retention in DataPulse:\n"
            "1. Use the built-in Window Function formula:\n"
            "   `RETENTION_RATE(cohort_date, activity_date, user_id)`\n"
            "2. Or in SQL view, write a window function:\n"
            "   `COUNT(DISTINCT user_id) OVER (PARTITION BY cohort_week ORDER BY activity_week)`\n"
            "3. Ensure your date filter is applied at the outer query level so boundary days aren't excluded prematurely."
        ),
        "resolution_summary": "Clarified non-additive nature of distinct counts across dimensions and recommended `RETENTION_RATE()` window function."
    },
    {
        "ticket_code": "DPA-207",
        "product": "DataPulse Analytics",
        "category": "API Integration",
        "customer_query": "Our automated pipeline is receiving HTTP 429 Too Many Requests when calling the DataPulse REST API to extract hourly sales figures.",
        "support_response": (
            "Hello! DataPulse Analytics applies rate limits on the REST API to protect query engine performance.\n\n"
            "Limits & Solution:\n"
            "1. Standard API keys are rate-limited to 60 requests/minute and 5 concurrent queries per key.\n"
            "2. Inspect the HTTP response headers:\n"
            "   - `X-RateLimit-Remaining`: Remaining calls in the current window.\n"
            "   - `Retry-After`: Seconds to wait before retrying.\n"
            "3. Recommendations:\n"
            "   - Implement exponential backoff with jitter in your script when receiving 429.\n"
            "   - Bulk extract: Use the `/api/v2/exports/async` endpoint to request a bulk batch download instead of polling single rows.\n"
            "   - If your organization requires higher throughput, contact your account manager to upgrade to Enterprise API tier (500 req/min)."
        ),
        "resolution_summary": "Explained 60 req/min rate limit, recommended `/api/v2/exports/async` bulk endpoint, and exponential backoff retry."
    },

    # ==========================================
    # PRODUCT 3: SecureAuth Gateway
    # ==========================================
    {
        "ticket_code": "SAG-301",
        "product": "SecureAuth Gateway",
        "category": "SAML 2.0 / SSO",
        "customer_query": "Users cannot sign in via Okta SAML SSO. SecureAuth Gateway displays error: 'Invalid SAML 2.0 Response: Audience URI mismatch or assertion expired'.",
        "support_response": (
            "Hello! An Audience URI mismatch occurs when the Entity ID configured in your Identity Provider (Okta) does not match the exact Audience URI expected by SecureAuth Gateway.\n\n"
            "To resolve this:\n"
            "1. In SecureAuth Gateway Admin -> SSO / Identity Providers -> Select your Okta SAML connector:\n"
            "   - Copy the exact 'Audience URI (SP Entity ID)' (e.g. `https://auth.yourdomain.com/saml/metadata`).\n"
            "   - Copy the 'Single Sign-On URL (ACS URL)' (e.g. `https://auth.yourdomain.com/saml/acs`).\n"
            "2. Open Okta Admin Portal -> Applications -> SecureAuth Gateway -> General -> SAML Settings:\n"
            "   - Paste the exact SP Entity ID into 'Audience URI (SP Entity ID)'. Check for trailing slashes.\n"
            "   - Check 'Assertion Encryption' matches (if enabled in SecureAuth, upload the public X.509 cert in Okta).\n"
            "3. Time Drift Check: If assertion expired immediately, verify NTP clock synchronization on your server. Allow up to 60 seconds clock skew under SecureAuth SAML Advanced Settings -> 'Clock Skew Tolerance: 60s'."
        ),
        "resolution_summary": "Aligned Okta SP Entity ID with SecureAuth Gateway Audience URI and set 60s clock skew tolerance."
    },
    {
        "ticket_code": "SAG-302",
        "product": "SecureAuth Gateway",
        "category": "MFA & Lockouts",
        "customer_query": "A VIP executive lost their phone with their Google Authenticator app and is completely locked out of SecureAuth. How can an administrator safely unlock them?",
        "support_response": (
            "Hello! Administrators can issue emergency one-time bypass codes or reset MFA enrollment securely.\n\n"
            "Emergency Recovery Steps:\n"
            "1. An Administrator must log in to the SecureAuth Admin Console.\n"
            "2. Go to Directory -> Users -> Search for the executive's email.\n"
            "3. In User Profile, click the 'Authentication Methods' tab.\n"
            "4. Choose one of two options:\n"
            "   - Option A (Recommended): Click 'Generate Temporary Bypass Code'. Select valid duration (e.g. 4 hours). Provide this 8-digit alphanumeric code to the user via a verified channel.\n"
            "   - Option B: Click 'Reset MFA Enrollment'. This forces the user to register a new authenticator device upon next password login.\n"
            "5. If their account was locked due to too many failed attempts, click 'Unlock Account'."
        ),
        "resolution_summary": "Guided admin to generate a temporary bypass code and reset MFA enrollment from Admin Console -> User Profile."
    },
    {
        "ticket_code": "SAG-303",
        "product": "SecureAuth Gateway",
        "category": "Session Management",
        "customer_query": "We configured user sessions for 8 hours, but users report getting logged out every 15 minutes when using our application through Nginx reverse proxy.",
        "support_response": (
            "Hi! This happens when an upstream reverse proxy (like Nginx, Cloudflare, or AWS ALB) strips or alters the `Set-Cookie` headers or client IP address, causing SecureAuth's session IP-binding security check to fail.\n\n"
            "To fix this in Nginx configuration:\n"
            "1. Ensure proxy headers are forwarded correctly:\n"
            "   `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`\n"
            "   `proxy_set_header X-Forwarded-Proto $scheme;`\n"
            "   `proxy_set_header Host $http_host;`\n"
            "2. Ensure cookie flags: In SecureAuth Admin -> Security -> Session Cookie, ensure `SameSite=Lax` and `Secure=true`.\n"
            "3. If your corporate users connect via mobile networks with dynamic shifting IPs, navigate to Admin -> Security -> Session Policies and toggle OFF 'Strict Client IP Binding' while leaving 'User-Agent Fingerprint Binding' ON."
        ),
        "resolution_summary": "Configured Nginx proxy headers and disabled Strict Client IP Binding to accommodate mobile IP rotations."
    },
    {
        "ticket_code": "SAG-304",
        "product": "SecureAuth Gateway",
        "category": "Active Directory / LDAP",
        "customer_query": "LDAP user synchronization failed with error 'LDAP Server Unavailable: Port 636 LDAPS connection rejected / Untrusted Certificate Authority'.",
        "support_response": (
            "Hello! When connecting to Active Directory over LDAPS (Port 636), SecureAuth Gateway validates the domain controller's SSL certificate against the trusted CA store.\n\n"
            "To fix this:\n"
            "1. Export your Internal Windows Server Active Directory Certificate Services Root CA certificate (in Base-64 `.cer` or `.pem` format).\n"
            "2. In SecureAuth Gateway Admin -> Directory Integrations -> Active Directory / LDAP:\n"
            "   - Under 'Certificate Authority', click 'Upload Custom CA Certificate' and select the exported `.pem`.\n"
            "3. Ensure the 'LDAP Hostname' field matches the Subject Alternative Name (SAN) of your domain controller (e.g. `dc01.company.local`, NOT the raw IP address `10.0.0.5`).\n"
            "4. Click 'Test LDAP Binding' using your service account credentials (`bind DN`)."
        ),
        "resolution_summary": "Uploaded internal Windows AD Root CA certificate to SecureAuth and configured FQDN instead of raw IP address."
    },
    {
        "ticket_code": "SAG-305",
        "product": "SecureAuth Gateway",
        "category": "SCIM Provisioning",
        "customer_query": "When an employee is deactivated in our HR system, SCIM 2.0 de-provisioning is not revoking their OAuth2 active refresh tokens in downstream apps.",
        "support_response": (
            "Hi there! By default, standard OAuth2 access tokens remain valid until their expiration TTL (e.g., 60 minutes) unless Token Revocation / OpenID Backchannel Logout is triggered.\n\n"
            "To enable instant revocation upon SCIM deprovisioning:\n"
            "1. Go to SecureAuth Admin -> Applications -> Select App -> OAuth2 / OIDC Settings.\n"
            "2. Enable 'Revoke Active Refresh and Access Tokens on User Deactivation'.\n"
            "3. Enable 'OpenID Connect Back-Channel Logout 1.0' and enter the downstream app's logout endpoint.\n"
            "4. In Admin Console -> Security -> SCIM Provisioning -> Advanced, check 'Cascade Deactivation to All Connected Sessions'.\n"
            "Now, when SCIM sends a `PATCH /Users/{id}` with `active: false`, all active sessions and tokens are terminated immediately within 500ms."
        ),
        "resolution_summary": "Enabled 'Revoke Active Refresh and Access Tokens on User Deactivation' and configured OIDC Back-Channel Logout."
    },
    {
        "ticket_code": "SAG-306",
        "product": "SecureAuth Gateway",
        "category": "FIDO2 / Passkeys",
        "customer_query": "Users attempting to register FIDO2 / WebAuthn hardware security keys (YubiKeys) fail on Firefox with error 'SecurityKeyNotSupported or NotAllowedError'.",
        "support_response": (
            "Hello! This issue is commonly caused by Firefox private browsing restrictions or an origin mismatch in the WebAuthn ceremony.\n\n"
            "Check the following points:\n"
            "1. Private Browsing: WebAuthn registration is disabled in Firefox Private Windows by default for privacy reasons. Advise users to perform initial key enrollment in a normal browser window.\n"
            "2. Origin / RP ID Mismatch: In SecureAuth Admin -> FIDO2 / WebAuthn Settings, ensure 'Relying Party ID (RP ID)' matches the exact top-level domain (e.g. `companyname.com` rather than a full URL with `https://`).\n"
            "3. Attestation Conveyance Preference: Set to 'None' or 'Indirect' unless your compliance requires 'Direct' attestation from hardware YubiKey manufacturers."
        ),
        "resolution_summary": "Advised enrolling in non-private window, confirmed RP ID domain formatting, and set attestation preference to 'None'."
    },
    {
        "ticket_code": "SAG-307",
        "product": "SecureAuth Gateway",
        "category": "Custom Branding & Domains",
        "customer_query": "How do we configure a custom login portal domain `login.ourcompany.com` with our own TLS certificate instead of the default `auth.secureauth-gateway.io`?",
        "support_response": (
            "Hello! Setting up a custom vanity domain is fully supported.\n\n"
            "Configuration steps:\n"
            "1. DNS Setup: Create a CNAME record in your DNS provider: `login.ourcompany.com` pointing to `custom.secureauth-gateway.io`.\n"
            "2. Admin Portal: Go to Admin Console -> Settings -> Custom Domain & Branding.\n"
            "3. Enter `login.ourcompany.com` in the Custom Domain field.\n"
            "4. SSL/TLS Certificate: Choose between:\n"
            "   - Automated Let's Encrypt (requires DNS CNAME verification, provisions in ~5 mins).\n"
            "   - Custom Certificate: Paste your PEM-formatted Certificate, Private Key, and Intermediate CA chain.\n"
            "5. Click 'Verify DNS & Deploy'. Once active, your logo, favicon, and primary color scheme will display on the custom URL."
        ),
        "resolution_summary": "Provided CNAME record instructions, SSL certificate installation options, and branding deployment steps."
    },

    # ==========================================
    # PRODUCT 4: DevFlow CI/CD
    # ==========================================
    {
        "ticket_code": "DF-401",
        "product": "DevFlow CI/CD",
        "category": "Docker & Runners",
        "customer_query": "Our build pipeline fails during `docker build` with error: 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?'.",
        "support_response": (
            "Hi! This error happens when a containerized pipeline runner does not have access to the Docker daemon socket or Docker-in-Docker (dind) service is not configured.\n\n"
            "Depending on your runner setup:\n"
            "1. If using DevFlow Cloud Runners: In your `.devflow-ci.yml`, add `services: [docker:dind]` under your job definition, and set environment variable `DOCKER_HOST: tcp://docker:2375` (or `tcp://docker:2376` with TLS).\n"
            "2. If using Self-Hosted Kubernetes Runner: Enable `privileged: true` in your runner's Helm values `values.yaml` under `runners.config.privileged`.\n"
            "3. If using VM/Docker Runner: Mount `/var/run/docker.sock:/var/run/docker.sock` in the runner's container volume mappings.\n"
            "Commit and re-run the pipeline; Docker build commands will execute normally."
        ),
        "resolution_summary": "Configured `docker:dind` service and DOCKER_HOST variable or mounted `/var/run/docker.sock` for self-hosted runners."
    },
    {
        "ticket_code": "DF-402",
        "product": "DevFlow CI/CD",
        "category": "Self-Hosted Runners",
        "customer_query": "Our self-hosted Linux build runner randomly drops into 'Offline' status in DevFlow UI every few days until we reboot the server.",
        "support_response": (
            "Hello! Random runner disconnections are typically caused by systemd process cgroup exhaustion, OOM kills during heavy builds, or network socket timeouts.\n\n"
            "To diagnose and resolve:\n"
            "1. Inspect system logs: `sudo journalctl -u devflow-runner -n 100 --no-pager`.\n"
            "2. If memory exhausted (OOM), enable a swap file and configure build memory limits in `.devflow-ci.yml`.\n"
            "3. Auto-restart resilience: Edit the systemd service file `/etc/systemd/system/devflow-runner.service`:\n"
            "   `Restart=always`\n"
            "   `RestartSec=10s`\n"
            "4. WebSocket Keepalive: In `/etc/devflow-runner/config.toml`, set `heartbeat_interval = 15` and `http_timeout = 30`.\n"
            "5. Run `sudo systemctl daemon-reload && sudo systemctl restart devflow-runner`."
        ),
        "resolution_summary": "Configured systemd `Restart=always`, 15s runner heartbeat interval, and checked OOM swap memory allocation."
    },
    {
        "ticket_code": "DF-403",
        "product": "DevFlow CI/CD",
        "category": "Secrets & Environment",
        "customer_query": "Our deployment script fails because secret environment variable `$PROD_DEPLOY_KEY` is completely empty inside the runner during execution on our staging branch.",
        "support_response": (
            "Hi there! In DevFlow CI/CD, secrets can have 'Protected' and 'Environment Scope' flags enabled to prevent exposure to non-production code.\n\n"
            "Check these settings:\n"
            "1. Navigate to Project Settings -> CI/CD -> Variables -> Edit `$PROD_DEPLOY_KEY`.\n"
            "2. Check 'Protected Variable': If this is checked, the secret is ONLY injected into pipelines running on Protected Branches (e.g. `main` or `production`). If your branch is `staging`, either protect `staging` in Settings -> Repository -> Protected Branches, or uncheck 'Protected' on the variable.\n"
            "3. Check 'Environment Scope': Ensure the variable's target environment matches the job's `environment:` key in your YAML file.\n"
            "4. Masking: Remember that masked variables must not contain special characters that violate regex standards."
        ),
        "resolution_summary": "Explained Protected Variable branch restrictions; advised unchecking Protected or marking branch as protected."
    },
    {
        "ticket_code": "DF-404",
        "product": "DevFlow CI/CD",
        "category": "Cache & Build Speed",
        "customer_query": "Every CI run re-downloads all npm node_modules and pip wheels from scratch, taking 12 minutes per commit. How do we configure build caching properly?",
        "support_response": (
            "Hello! You can dramatically reduce build times to under 1 minute by setting up deterministic cache keys based on package lockfiles.\n\n"
            "Example `.devflow-ci.yml` cache configuration:\n"
            "```yaml\n"
            "cache:\n"
            "  key:\n"
            "    files:\n"
            "      - package-lock.json\n"
            "      - requirements.txt\n"
            "  paths:\n"
            "    - .npm/\n"
            "    - node_modules/\n"
            "    - .cache/pip/\n"
            "```\n"
            "Key points:\n"
            "1. Use `npm ci --cache .npm --prefer-offline`.\n"
            "2. For Python, use `pip install --cache-dir .cache/pip -r requirements.txt`.\n"
            "3. If using distributed runners, configure an S3 or MinIO Distributed Cache backend in Project Settings -> CI/CD -> Runner Caching."
        ),
        "resolution_summary": "Configured lockfile-based cache key and specified local `.npm` and pip cache paths to avoid redownloading."
    },
    {
        "ticket_code": "DF-405",
        "product": "DevFlow CI/CD",
        "category": "Kubernetes & Deployment",
        "customer_query": "Our deploy step to Amazon EKS fails with error: 'Failed to pull image ... ImagePullBackOff: rpc error: 401 Unauthorized'.",
        "support_response": (
            "Hi! This happens when the Kubernetes cluster does not have valid AWS ECR registry credentials to pull private container images.\n\n"
            "To fix this:\n"
            "1. Option A (Recommended - IAM Roles for Service Accounts / IRSA):\n"
            "   Attach the `AmazonEC2ContainerRegistryReadOnly` policy to your EKS node group or pod service account.\n"
            "2. Option B (Kubernetes Secret):\n"
            "   In your DevFlow pipeline deployment job, generate and refresh the ECR image pull secret before deploying:\n"
            "   ```bash\n"
            "   TOKEN=$(aws ecr get-login-password --region us-east-1)\n"
            "   kubectl create secret docker-registry ecr-secret \\\n"
            "     --docker-server=123456789.dkr.ecr.us-east-1.amazonaws.com \\\n"
            "     --docker-username=AWS \\\n"
            "     --docker-password=$TOKEN \\\n"
            "     --dry-run=client -o yaml | kubectl apply -f -\n"
            "   ```\n"
            "3. Reference `imagePullSecrets: [{name: ecr-secret}]` in your Kubernetes Deployment spec."
        ),
        "resolution_summary": "Configured EKS IAM IRSA permissions or refreshed `imagePullSecrets` docker-registry token for private ECR."
    },
    {
        "ticket_code": "DF-406",
        "product": "DevFlow CI/CD",
        "category": "Webhooks & Triggers",
        "customer_query": "Pull requests merged in GitHub are not triggering our automatic deployment pipeline in DevFlow CI/CD.",
        "support_response": (
            "Hello! Let's troubleshoot why GitHub Webhook events are not reaching or triggering your pipeline.\n\n"
            "Troubleshooting steps:\n"
            "1. Check GitHub Webhook Deliveries: In your GitHub repo -> Settings -> Webhooks -> Select DevFlow webhook -> 'Recent Deliveries'.\n"
            "   - If response is 403/401: The Webhook Secret Token in DevFlow Project Settings does not match GitHub's secret.\n"
            "   - If response is 404 or connection timed out: Verify the DevFlow ingress URL is reachable.\n"
            "2. Check Event Triggers: In GitHub webhook settings, ensure 'Pull requests' and 'Pushes' are checked.\n"
            "3. Check Pipeline Rules: In `.devflow-ci.yml`, verify your job conditions:\n"
            "   ```yaml\n"
            "   rules:\n"
            "     - if: '$CI_COMMIT_BRANCH == \"main\"'\n"
            "       when: always\n"
            "   ```\n"
            "   If you had `rules: [if: '$CI_PIPELINE_SOURCE == \"merge_request_event\"']`, note that after merging, the event becomes a `push` to the target branch!"
        ),
        "resolution_summary": "Checked GitHub webhook delivery logs, verified secret token match, and adjusted CI rules for push to main branch."
    },
    {
        "ticket_code": "DF-407",
        "product": "DevFlow CI/CD",
        "category": "Rollbacks & Monitoring",
        "customer_query": "How do we configure DevFlow to automatically roll back a production deployment if our health check returns HTTP 500 or 503 after deployment?",
        "support_response": (
            "Hi there! DevFlow CI/CD supports automated Canary and Blue/Green Rollback policies via post-deployment health verification.\n\n"
            "To configure auto-rollback:\n"
            "1. In your `.devflow-ci.yml`, use the `post_deploy_check` step:\n"
            "```yaml\n"
            "deploy_prod:\n"
            "  stage: deploy\n"
            "  script:\n"
            "    - helm upgrade --install myapp ./chart\n"
            "  health_check:\n"
            "    url: https://myapp.com/healthz\n"
            "    expected_status: 200\n"
            "    interval: 5s\n"
            "    timeout: 60s\n"
            "  on_failure:\n"
            "    script:\n"
            "      - echo 'Health check failed! Rolling back...'\n"
            "      - helm rollback myapp 0\n"
            "      - notify-slack --channel #prod-alerts 'Production auto-rolled back!'\n"
            "```\n"
            "2. If `expected_status` is not met within the timeout window, DevFlow aborts and runs the `on_failure` script automatically."
        ),
        "resolution_summary": "Configured `health_check` block and `on_failure` automated Helm rollback hook in `.devflow-ci.yml`."
    }
]


def seed_database():
    """Seeds the SQLite database with historical support tickets and generates embeddings."""
    print("=" * 60)
    print("Initializing Database and Seeding Historical Customer Support Data")
    print("=" * 60)

    # Initialize schema
    database.init_db()

    # Check if already seeded
    existing_count = database.count_tickets()
    if existing_count >= len(HISTORICAL_TICKETS):
        print(f"Database already contains {existing_count} tickets. Checking if embeddings exist...")
        all_t = database.get_all_tickets_for_product()
        if all(t.get("embedding") for t in all_t):
            print("All tickets already have embeddings. Skipping re-seeding.")
            return

    # Initialize Embeddings model
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[!] Warning: OPENAI_API_KEY not found in environment. Inserting tickets without embeddings.")
        embeddings_model = None
    else:
        print("Using OpenAIEmbeddings (text-embedding-3-small) to embed historical QA pairs...")
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )

    # Prepare texts for embedding: customer_query + resolution_summary + product
    texts_to_embed = [
        f"Product: {t['product']}\nCategory: {t['category']}\nQuery: {t['customer_query']}\nResolution: {t['resolution_summary']}\nDetails: {t['support_response']}"
        for t in HISTORICAL_TICKETS
    ]

    embeddings = [None] * len(HISTORICAL_TICKETS)
    if embeddings_model:
        try:
            print(f"Generating embeddings for {len(texts_to_embed)} historical support tickets...")
            embeddings = embeddings_model.embed_documents(texts_to_embed)
            print("Embeddings generated successfully!")
        except Exception as e:
            print(f"[!] Warning: Failed to compute embeddings via OpenAI: {e}")
            print("Tickets will be stored and keyword search will be used as fallback.")

    # Insert into database
    for i, t in enumerate(HISTORICAL_TICKETS):
        emb = embeddings[i] if i < len(embeddings) else None
        database.insert_ticket(
            ticket_code=t["ticket_code"],
            product=t["product"],
            category=t["category"],
            customer_query=t["customer_query"],
            support_response=t["support_response"],
            resolution_summary=t["resolution_summary"],
            embedding=emb
        )

    print(f"\n[OK] Successfully seeded {len(HISTORICAL_TICKETS)} historical tickets across products:")
    for p in database.get_distinct_products():
        count = len(database.get_all_tickets_for_product(p))
        print(f"  - {p}: {count} historical cases")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
