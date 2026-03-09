# Encryption Key Management and Rotation Policy

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

---

## 1. Purpose and Scope

This policy governs the management, storage, rotation, and compromise response for all cryptographic keys and secrets used by the BLACKSITE platform. Proper key management is a foundational control for maintaining the confidentiality of the encrypted database and the integrity of user sessions and external API communications.

**In scope:**
- BLACKSITE database encryption key (SQLCipher / pysqlcipher3 1.2.0)
- Application session secret key (`SECRET_KEY` environment variable)
- Groq API key
- Any future API keys, signing keys, or secrets introduced to the platform

**Out of scope:**
- TLS certificates (managed automatically by Caddy/ACME; separate lifecycle)
- SSH host keys (managed by OS)
- Backup encryption at the NAS layer

---

## 2. Key Types and Classification

| Key / Secret | Type | Classification | Storage Location |
|-------------|------|---------------|-----------------|
| `DB_ENCRYPTION_KEY` | AES-256 symmetric (SQLCipher) | **Critical** — loss = data inaccessible; compromise = data exposed | systemd service unit `Environment=` |
| `SECRET_KEY` | HMAC secret (session signing) | **High** — compromise allows session forgery | systemd service unit `Environment=` |
| `GROQ_API_KEY` | API bearer token | **Medium** — compromise enables unauthorized AI API use at operator's expense | systemd service unit `Environment=` |

**Classification definitions:**
- **Critical:** Loss or compromise directly enables access to all stored data or renders the platform inoperable
- **High:** Compromise enables privilege escalation or impersonation of users
- **Medium:** Compromise causes financial or operational harm but does not directly expose customer data

---

## 3. Key Storage Requirements

**All keys and secrets must:**

1. Be stored only in the systemd service unit file as `Environment=` entries:
   ```
   /etc/systemd/system/blacksite.service
   ```
2. **Never** be stored in:
   - Application source code (`.py` files)
   - Configuration files committed to version control (`.env`, `config.yml`, etc.)
   - Application logs
   - Environment variables passed via shell history (use `systemctl edit` or direct file editing)
   - Docker compose files, `.env` files in the project directory

3. The service unit file must be owned by root and readable only by root:
   ```bash
   sudo chown root:root /etc/systemd/system/blacksite.service
   sudo chmod 600 /etc/systemd/system/blacksite.service
   ```

4. The graycat user account (which runs the service) inherits the environment variables at runtime without being able to read the service file directly.

5. Emergency offline copy: A printed or air-gapped copy of `DB_ENCRYPTION_KEY` must be stored in a physically secure location. Without this key, the database is unrecoverable. This is the single most critical secret in the system.

---

## 4. Rotation Schedule

| Key / Secret | Rotation Frequency | Trigger for Immediate Rotation |
|-------------|-------------------|-------------------------------|
| `DB_ENCRYPTION_KEY` | Annually | Suspected or confirmed compromise; staff departure with knowledge of the key; host compromise |
| `SECRET_KEY` | Annually | Suspected or confirmed compromise; any indication of session forgery; staff departure |
| `GROQ_API_KEY` | Every 6 months, or upon staff departure | Suspected unauthorized use; staff departure; API key appears in logs or code |

**Annual rotation window:** Each March (aligned with this policy's review date) is the default rotation window for all keys unless a trigger event requires earlier rotation.

**Next scheduled rotation:** 2027-03 (unless triggered earlier)

---

## 5. DB Encryption Key Rotation Procedure

This is the highest-risk rotation operation. Follow exactly.

### Prerequisites
- Full database backup completed and verified within the past 24 hours
- A second terminal session open and ready as a fallback
- Maintenance window communicated to active users (service will be offline ~5–15 minutes)

### Step 1: Stop the service
```bash
sudo systemctl stop blacksite
```

Confirm no processes are holding the DB open:
```bash
lsof /home/graycat/projects/blacksite/data/blacksite.db
# Should return no output
```

### Step 2: Backup the current database
```bash
cp /home/graycat/projects/blacksite/data/blacksite.db \
   /home/graycat/projects/blacksite/data/blacksite.db.pre-rotation-$(date +%Y%m%d%H%M%S)
```

Verify backup integrity:
```bash
# (Run through app context or sqlcipher CLI with old key)
# Confirm file size matches original
ls -lh /home/graycat/projects/blacksite/data/blacksite.db*
```

### Step 3: Generate new key
```bash
# Generate a cryptographically random 64-character hex key
NEW_KEY=$(openssl rand -hex 32)
echo "New key (save this NOW to offline storage): $NEW_KEY"
```

**Save the new key to offline storage immediately before proceeding.**

### Step 4: Re-encrypt the database with the new key

SQLCipher supports re-keying without full DB export/import:
```bash
# Using sqlcipher CLI (must be available on the host)
# Replace OLD_KEY with current key from service unit
sqlcipher /home/graycat/projects/blacksite/data/blacksite.db <<EOF
PRAGMA key = 'OLD_KEY_HERE';
PRAGMA rekey = '$NEW_KEY';
EOF
```

If sqlcipher CLI is not available, use the Python approach:
```python
# run as: python3 rekey.py (with OLD_KEY and NEW_KEY set)
import os
from pysqlcipher3 import dbapi2 as sqlite

conn = sqlite.connect('/home/graycat/projects/blacksite/data/blacksite.db')
conn.execute(f"PRAGMA key = '{os.environ['OLD_KEY']}'")
conn.execute(f"PRAGMA rekey = '{os.environ['NEW_KEY']}'")
conn.close()
print("Re-key complete")
```

### Step 5: Verify the new key opens the database
```bash
python3 -c "
import os
from pysqlcipher3 import dbapi2 as sqlite
conn = sqlite.connect('/home/graycat/projects/blacksite/data/blacksite.db')
conn.execute(\"PRAGMA key = '\" + os.environ['NEW_KEY'] + \"'\")
result = conn.execute('PRAGMA integrity_check').fetchone()
print('Integrity check:', result)
conn.execute('SELECT count(*) FROM sqlite_master').fetchone()
print('Schema accessible: OK')
conn.close()
"
```

Expected output: `Integrity check: ('ok',)` and `Schema accessible: OK`

If this fails, **stop immediately** and restore from the pre-rotation backup in Step 2.

### Step 6: Update the systemd service unit

```bash
sudo systemctl edit --full blacksite
# In the editor, update: Environment="DB_ENCRYPTION_KEY=NEW_KEY_HERE"
# Save and exit
sudo systemctl daemon-reload
```

### Step 7: Start the service and verify
```bash
sudo systemctl start blacksite
curl -s http://127.0.0.1:8100/health
# Verify login, data access, and audit log entry
```

### Step 8: Securely delete the pre-rotation backup
```bash
shred -vzn 3 /home/graycat/projects/blacksite/data/blacksite.db.pre-rotation-*
```

### Step 9: Log the rotation event

Record in `/home/graycat/docs/key-rotation-log.md`:
```
[Date] DB_ENCRYPTION_KEY rotated. Rotation completed by: [name]. Trigger: [scheduled/compromised/departure]. Verified: Yes. Old backup securely deleted: Yes.
```

---

## 6. SECRET_KEY Rotation Procedure

Rotating `SECRET_KEY` immediately invalidates all active user sessions. All logged-in users will be logged out.

```bash
# Generate new secret key
NEW_SECRET=$(openssl rand -hex 32)

# Update service unit
sudo systemctl edit --full blacksite
# Update: Environment="SECRET_KEY=NEW_SECRET_HERE"
sudo systemctl daemon-reload
sudo systemctl restart blacksite

# Verify health
curl -s http://127.0.0.1:8100/health
```

If rotating due to suspected session forgery, also review the audit log for any anomalous activity in the period before rotation.

---

## 7. GROQ_API_KEY Rotation Procedure

1. Log into console.groq.com and generate a new API key
2. Update the service unit (`sudo systemctl edit --full blacksite`) with the new key
3. `sudo systemctl daemon-reload && sudo systemctl restart blacksite`
4. Verify AI assistant function works (test query in the platform)
5. Revoke the old API key in the Groq console
6. Log the rotation event

---

## 8. Key Compromise Response Procedure

If a key is known or suspected to have been compromised (found in logs, committed to git, disclosed to unauthorized party):

1. **Immediately rotate the affected key** — do not wait for the scheduled window
2. Review audit logs for the period of suspected compromise to assess unauthorized access
3. If `DB_ENCRYPTION_KEY` was compromised, treat as a P1 security incident (see Incident Response Runbook) and notify affected customers
4. If `GROQ_API_KEY` was compromised, revoke it in the Groq console immediately and monitor for unauthorized API charges
5. Conduct a root cause analysis: How was the key exposed? (git commit, log output, shoulder surfing, system compromise)
6. Add preventive controls to prevent recurrence

---

## 9. Access Control

- The systemd service unit file (`/etc/systemd/system/blacksite.service`) must be owned by root and mode 600
- Only the `root` user and the `graycat` user (service runner) have access to the host
- No other users should be granted access to the production host without explicit authorization
- Regular access reviews (see Personnel Security Procedures) confirm no unauthorized accounts exist

---

## 10. Audit Trail Requirements

All key rotation events must be logged in `/home/graycat/docs/key-rotation-log.md` with:
- Date and time of rotation
- Key identifier (which key was rotated)
- Trigger reason (scheduled / suspected compromise / staff departure / other)
- Performed by (name)
- Verification result (pass/fail)
- Disposition of old key material (backup deleted / N/A)

This log is itself a security artifact and should be included in the annual backup.

---

## 11. References

- NIST SP 800-57 Part 1 (Key Management Recommendations)
- NIST SP 800-53 SC-12 (Cryptographic Key Establishment and Management), SC-28 (Protection of Information at Rest)
- pysqlcipher3 1.2.0 documentation
- SQLCipher documentation: https://www.zetetic.net/sqlcipher/sqlcipher-api/
