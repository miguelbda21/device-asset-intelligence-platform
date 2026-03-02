# 📦 Device Asset Intelligence Platform

> Enterprise Data Engineering + FastAPI + AWS Deployment
---

# 🖥️ Overview

> The Device Asset Intelligence Platform is an end-to-end data engineering solution that:

* Extracts asset data from S3

* Transforms and enriches device lifecycle metrics

* Loads data into PostgreSQL (AWS RDS)

* Exposes analytics via a FastAPI REST API

* Deploys to AWS EC2 with Nginx reverse proxy

> This project demonstrates:

* Python-based ETL pipelines

* Cloud-native architecture (AWS)

* REST API development

* Production deployment practices

---

# 🏗️ Architecture
```
Users
   ↓
EC2 (Nginx)
   ↓
FastAPI (Uvicorn)
   ↓
PostgreSQL (RDS)
   ↓
S3 (Raw / Staging / Warehouse)

```
---

# 📁 Project Structure
```
device-asset-intelligence-platform/
│
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── routers/
│   │
│   ├── etl/
│   │   ├── extract.py
│   │   ├── transform.py
│   │   └── load.py
│
├── data/
│   ├── staging/
│   ├── warehouse/
│
├── requirements.txt
└── README.md
```
---

# 🚀 AWS Setup Guide (Clean Deployment Checklist)
### 1️⃣ Create AWS Account

* Enable MFA on root account

* Do NOT use root for daily work

### 2️⃣ Create IAM Admin User

IAM → Users → Create User

* Enable programmatic + console access

* Attach: AdministratorAccess

* Save Access Key & Secret

Configure locally:
```bash
aws configure
```
### 3️⃣ Create S3 Bucket

S3 → Create bucket

Example:
```bash
device-asset-platform-data
```
Create structure:
```bash
raw/
staging/
warehouse/
logs/
```
### 4️⃣ Create RDS PostgreSQL

RDS → Create database

Engine: PostgreSQL

* Template: Free Tier

* Instance: db.t3.micro

* Public access: YES (learning phase)

* Storage: 20GB

Security group:

* Allow port 5432 from YOUR IP only

### 5️⃣ Launch EC2 Instance

EC2 → Launch Instance

* AMI: Amazon Linux 2023

* Instance: t2.micro

* Allow:

  * SSH (22) from your IP

  * HTTP (80)

  * HTTPS (443)

Download key pair (.pem).

## 🔐 SSH Into EC2
```bash
ssh -i your-key.pem ec2-user@<EC2-Public-IP>
```
## 🛠️ Install Dependencies
```bash
sudo yum update -y
sudo yum install git -y
sudo yum install python3 -y
sudo yum install nginx -y
```
Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
## 📥 Clone Repository
```bash

```
