# Oracle Cloud Always Free VM Setup

## 1. Create the VM (one-time, ~10 min)

1. Sign up at https://cloud.oracle.com/free (requires card verification, no charge).
2. Console → Compute → Instances → Create Instance.
3. Settings:
   - Name: `routinetraderbot`
   - Image: **Canonical Ubuntu 24.04** (ARM64 Ampere)
   - Shape: **VM.Standard.A1.Flex** — 1 OCPU / 6 GB RAM is enough (free: up to 4 OCPU / 24 GB total)
   - Networking: default VCN, public IPv4
   - SSH key: upload your `~/.ssh/id_rsa.pub` (or generate one)
4. Create. Note the **public IP**.

## 2. Open ports

Default VCN security list allows SSH (22) already. The bot only needs outbound HTTPS (443) — open by default.

## 3. Deploy

From your local machine:

```bash
cd /home/mad/trading-bot
./scripts/deploy-oracle.sh ubuntu@<VM_IP> ~/.ssh/id_rsa
```

Then sync your secrets once:

```bash
scp -i ~/.ssh/id_rsa .env ubuntu@<VM_IP>:/home/ubuntu/routinetraderbot/.env
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP> sudo systemctl restart trading-bot
```

## 4. Operate

```bash
# Live logs
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP> journalctl -u trading-bot -f

# Restart
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP> sudo systemctl restart trading-bot

# Stop
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP> sudo systemctl stop trading-bot
```

## 5. Health monitoring

The bot sends a Telegram heartbeat every 30 min. The watchdog (`scripts/watchdog.sh`) also restarts the service if the process dies. Install it via cron on the VM:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP>
(crontab -l 2>/dev/null; echo "* * * * * /home/ubuntu/routinetraderbot/scripts/watchdog.sh") | crontab -
```

## Cost

$0. Always Free tier covers: 4 ARM OCPUs, 24 GB RAM, 200 GB storage, 10 TB egress/mo. This bot uses a tiny fraction of that.
