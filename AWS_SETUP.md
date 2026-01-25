# AWS Infrastructure Setup Guide

I have set up **Terraform** to automate your server creation.

## Prerequisites
1.  **AWS Credentials**: You need your AWS Access Key and Secret Key.
    *   Go to **AWS IAM Console** -> Users -> Create User -> Attach `AdministratorAccess` (for simplicity) -> Security Credentials -> Create Access Key.
2.  **Export Keys**:
    Run this in your terminal (replace with your real keys):
    ```bash
    export AWS_ACCESS_KEY_ID="AKIA..."
    export AWS_SECRET_ACCESS_KEY="wJalr..."
    ```

## 🚀 How to Launch the Server
1.  **Initialize Terraform**:
    ```bash
    cd infrastructure
    terraform init
    ```
2.  **Review the Plan**:
    ```bash
    terraform plan
    ```
    (This shows you what will be created: 1 Instance, 1 Security Group, 1 Key Pair).
3.  **Apply (create the server)**:
    ```bash
    terraform apply
    ```
    *   Type `yes` when asked.

## 🔑 Accessing the Server
**Success!** Your server is live.

**Public IP:** `100.48.72.44`
**SSH Key:** `secrets/philly_key.pem`

**To connect:**
1.  Open Terminal.
2.  Run this exact command:
    ```bash
    ssh -i secrets/philly_key.pem ubuntu@100.48.72.44
    ```

## 📦 Next Steps (Deploying the App on AWS)
Once you are logged into the server:
1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/your-username/Philly-P-Sniper.git
    cd Philly-P-Sniper
    ```
2.  **Setup Keys**:
    Create a `.env` file with your API keys:
    ```bash
    nano .env
    # Paste your keys here (ODDS_API_KEY, DATABASE_URL, etc.)
    # Ctrl+O to save, Ctrl+X to exit
    ```
3.  **Run with Docker**:
    ```bash
    sudo docker-compose up -d --build
    ```
4.  **View Dashboard**:
    Open `http://100.48.72.44` in your browser. (No port needed!)

## 🧹 Tearing Down (Stop Billing)
If you want to delete everything:
```bash
terraform destroy
```
