# 🌐 Domain Setup Guide (AWS & External)

## Option A: Registering via AWS Route 53 (Recommended)
Since your infrastructure is on AWS, this is the easiest path.

1.  **Register Domain**:
    -   Log in to **AWS Console** and search for **"Route 53"**.
    -   Click **"Registered domains"** -> **"Register Domain"**.
    -   Search for `phillyedge.ai` (or your choice) and complete checkout.
    -   Wait 15-30 minutes for email verification/approval.

2.  **Point it to your Server**:
    -   Go to **"Hosted zones"** in Route 53.
    -   Click your new domain name.
    -   **Create Record**:
        -   **Record Name**: Leave empty (for root) or `www`.
        -   **Record Type**: `A - Routes traffic to an IPv4 address`.
        -   **Value**: `100.48.72.44` (Your Server IP).
    -   Click **Create records**.

---

## Option B: Registering via Namecheap/GoDaddy (Legacy)
If you already bought a domain elsewhere:

1.  **Log in** to your registrar (Namecheap/GoDaddy).
2.  Go to **Advanced DNS** (or DNS Management).
3.  **Add an 'A Record'**:
    -   **Type**: `A Record`
    -   **Host**: `@`
    -   **Value**: `100.48.72.44`
    -   **TTL**: Automatic (or 1 min)
4.  **(Optional) Add a 'CNAME'** for `www`:
    -   **Type**: `CNAME Record`
    -   **Host**: `www`
    -   **Value**: `yourdomain.com`
