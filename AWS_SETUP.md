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
Once finished, Terraform will output your **Server IP** and the **SSH Command**.
A file named `philly_key.pem` will be created in the `infrastructure/` folder.

**To connect:**
```bash
cd infrastructure
ssh -i philly_key.pem ubuntu@<IP_ADDRESS>
```

## 🧹 Tearing Down (Stop Billing)
If you want to delete everything:
```bash
terraform destroy
```
