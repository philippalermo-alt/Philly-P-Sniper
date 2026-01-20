# 🌐 Custom Domain Setup Guide for Philly P Sniper

This guide walks you through purchasing a domain, configuring it with AWS, and setting up secure HTTPS access.

## 1. Research & Purchase Domain
Since your infrastructure is already on AWS, the simplest path is **Amazon Route 53**. It integrates natively with your EC2 instance.

### Option A: Amazon Route 53 (Blocked?)
> **⚠️ Note**: AWS often blocks new accounts from registering domains for anti-fraud reasons. If you see an error saying "We can't finish registering your domain", **skip to Option B**. Resolving this with AWS Support can take days.

### Option B: Namecheap / GoDaddy (Recommended Alternative)
 Since AWS rejected the registration, this is the fastest path.
- **Cost**: ~$10/year.
- **How to Buy**:
    1. Go to [Namecheap.com](https://www.namecheap.com).
    2. Buy your domain (`phillypsniper.com`).
    3. **Important**: You do *not* need to buy their "Hosting" or "SSL" add-ons. You just need the domain.
    4. Once bought, go to **Domain List** > **Manage** > **Advanced DNS**.
    5. **Delete** any existing records.
    6. Add a new **A Record**:
       - Host: `@`
       - Value: `100.48.72.44`
       - TTL: `Automatic` (or 5 min)
    7. Add a new **CNAME Record** (for "www"):
       - Host: `www`
       - Value: `phillypsniper.com`
       - TTL: `Automatic`

*That is it. You do not need to transfer the domain to AWS. Just pointing the DNS records is enough.*

---

## 2. Connect Domain to Your Server
Once purchased, you need to tell the domain to send traffic to your EC2 IP Address (`100.48.72.44`).

### If using Rate 53:
1. Go to **Route 53** > **Hosted Zones** > Click your domain.
2. Click **Create Record**.
    - **Record Name**: Leave empty (for root domain `phillypsniper.com`) or `www`.
    - **Record Type**: `A` (Routes traffic to an IPv4 address).
    - **Value**: `100.48.72.44`
    - **TTL**: `300` (5 minutes).
3. Click **Create records**.
4. Repeat for `www` (Record Name: `www`, Value: `100.48.72.44`).

### If using Namecheap/GoDaddy:
1. Log into their dashboard > **DNS Settings**.
2. Create an **A Record**:
    - **Host**: `@`
    - **Value**: `100.48.72.44`
3. Create a **CNAME Record**:
    - **Host**: `www`
    - **Value**: `phillypsniper.com` (or your domain).

---

## 3. Enable HTTPS (Secure Padlock 🔒)
Currently, your site is HTTP. To get the secure padlock, use **Certbot** (free).

### Step 3.1: Install Certbot on AWS
Login to your server:
```bash
sniper
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

*(Note: If you are not running Nginx yet, you might need to install it to act as a reverse proxy, or use Streamlit's native SSL if supported, but Nginx is best practice).*

### Step 3.2: Set up Nginx Proxy (Standard for Streamlit)
Streamlit runs on port 8501. Standard web traffic uses port 80/443. We need Nginx to bridge them.

1. **Install Nginx**:
   ```bash
   sudo apt-get install -y nginx
   ```

2. **Configure Nginx**:
   ```bash
   sudo nano /etc/nginx/sites-available/default
   ```
   Replace contents with:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```
   *(Replace `yourdomain.com` with your actual domain)*.

3. **Restart Nginx**:
   ```bash
   sudo systemctl restart nginx
   ```

### Step 3.3: Activate SSL
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Follow prompts (Enter email, Agree to TOS). Certbot will auto-configure SSL.

---

## Summary Checklist
- [ ] Buy Domain (Route 53 recommended).
- [ ] Create `A Record` pointing to `100.48.72.44`.
- [ ] Install Nginx & Certbot on Server.
- [ ] Run `certbot` to enable HTTPS.
