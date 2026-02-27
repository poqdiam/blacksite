"""
BLACKSITE — Control remediation dictionary.

Provides per-control (and family-level fallback) remediation guidance:
  artifacts  — evidence/documentation required
  commands   — copy-paste shell commands that directly address the gap
  suggestion — brief narrative of what to do

Usage:
    from app.remediation import get_remediation
    data = get_remediation("ac-2")
"""
from __future__ import annotations
from typing import Dict, List, Any

# ---------------------------------------------------------------------------
# Control-specific entries
# Format: control_id → {artifacts, commands, suggestion}
# Commands: prefixed with "# <description>" comment lines
# ---------------------------------------------------------------------------
REMEDIATION: Dict[str, Dict[str, Any]] = {

    # ── AC — Access Control ──────────────────────────────────────────────────
    "ac-1": {
        "artifacts": ["Access Control Policy (signed, dated)", "Procedures doc referencing policy version"],
        "commands": [],
        "suggestion": "Draft policy using NIST SP 800-53 Appendix J templates. Must include purpose, scope, roles, enforcement, and review frequency (at least annually).",
    },
    "ac-2": {
        "artifacts": ["Account inventory (CSV/CMDB)", "Access request forms", "Account review records (quarterly)"],
        "commands": [
            "# Full account inventory with last login:\nlastlog | sort -k1",
            "# Accounts with no password set:\nsudo awk -F: '($2==\"\"){print $1}' /etc/shadow",
            "# Accounts inactive >90 days:\nlastlog -b 90 | tail -n +2 | awk '{print $1}'",
            "# Disable inactive account:\nsudo usermod -L -e 1 <username>",
            "# Enumerate sudo/admin members:\ngetent group sudo wheel adm | tr ':' '\\n'",
            "# AD/LDAP: export account list:\nldapsearch -H ldap://<dc> -b 'DC=corp,DC=com' '(objectClass=user)' sAMAccountName pwdLastSet | grep -E 'sAM|pwd'",
        ],
        "suggestion": "Implement quarterly access reviews. Automate account disabling after 90 days of inactivity. Use a ticketing system as the authoritative access request record.",
    },
    "ac-3": {
        "artifacts": ["Access control matrix (role/resource mapping)", "DAC/MAC implementation evidence", "File permission audit"],
        "commands": [
            "# Find world-writable files (critical paths):\nfind /etc /var /srv -type f -perm -0002 2>/dev/null",
            "# Find SUID/SGID binaries:\nfind / -type f \\( -perm -4000 -o -perm -2000 \\) 2>/dev/null | sort",
            "# Audit sudoers:\nsudo cat /etc/sudoers; sudo ls /etc/sudoers.d/",
            "# Check ACLs on sensitive dirs:\ngetfacl /etc/shadow /etc/sudoers /var/log",
        ],
        "suggestion": "Implement role-based access control (RBAC). Remove all world-writable files outside /tmp. Document and justify every SUID binary. Enforce least privilege via sudoers with specific command whitelisting.",
    },
    "ac-4": {
        "artifacts": ["Network segmentation diagram", "Firewall ruleset export", "Data flow diagram"],
        "commands": [
            "# List firewall rules:\nsudo iptables -L -n -v --line-numbers 2>/dev/null || sudo nft list ruleset",
            "# UFW rules:\nsudo ufw status verbose",
            "# Active connections and listening ports:\nss -tulnp",
            "# Check default FORWARD policy:\nsudo iptables -L FORWARD | head -3",
        ],
        "suggestion": "Implement deny-by-default firewall policy. Document all inter-zone flows in a data flow diagram. Use VLANs + firewall rules to enforce boundaries.",
    },
    "ac-5": {
        "artifacts": ["Separation of duties matrix", "Role conflict analysis", "Privileged account list"],
        "commands": [
            "# Users with both developer and admin roles:\ngetent group developers admins sudo | grep -oP '(?<=:)[^:]+$'",
            "# Check for root direct login capability:\ngrep '^PermitRootLogin' /etc/ssh/sshd_config",
        ],
        "suggestion": "Build a role conflict matrix. No single user should be able to both request and approve access, or develop and deploy code. Enforce via IAM policies.",
    },
    "ac-6": {
        "artifacts": ["Privileged access list", "Justification records for admin roles", "Sudo audit log"],
        "commands": [
            "# Users with UID 0 (all root-equivalent):\nawk -F: '$3==0{print $1}' /etc/passwd",
            "# Full sudo command audit (last 30 days):\ngrep 'sudo:' /var/log/auth.log | tail -200",
            "# Capabilities assigned to binaries:\nfind /usr/bin /usr/sbin -executable -type f | xargs getcap 2>/dev/null",
        ],
        "suggestion": "Enumerate all privileged access. Require documented justification for each admin account. Use sudo with specific command whitelisting rather than ALL. Log and alert on all privileged command executions.",
    },
    "ac-7": {
        "artifacts": ["Account lockout policy documentation", "PAM configuration", "Failed login monitoring evidence"],
        "commands": [
            "# Check PAM lockout (faillock/pam_tally2):\ncat /etc/pam.d/common-auth | grep -E 'faillock|tally'",
            "# View currently locked accounts:\nsudo faillock --user <username>",
            "# Reset lockout:\nsudo faillock --user <username> --reset",
            "# Check /etc/security/faillock.conf:\ncat /etc/security/faillock.conf 2>/dev/null",
        ],
        "suggestion": "Configure PAM faillock: deny=5 unlock_time=900 (15 min). Alert on lockout events. For web apps, add CAPTCHA after 3 failures and progressive delays.",
    },
    "ac-11": {
        "artifacts": ["Session timeout configuration", "Screen lock policy evidence"],
        "commands": [
            "# Check TMOUT (CLI session timeout):\ngrep -r 'TMOUT' /etc/profile /etc/profile.d/ /etc/bash.bashrc",
            "# Set session timeout (add to /etc/profile.d/timeout.sh):\necho 'export TMOUT=900\\nreadonly TMOUT' | sudo tee /etc/profile.d/timeout.sh",
            "# Apache/Nginx session timeout:\ngrep -r 'timeout\\|session' /etc/apache2/ /etc/nginx/ 2>/dev/null | head -20",
        ],
        "suggestion": "Set TMOUT=900 (15 min) readonly in /etc/profile.d/ for all CLI sessions. Configure web application session timeout to 30 minutes maximum.",
    },
    "ac-17": {
        "artifacts": ["Remote access policy", "VPN configuration export", "MFA enrollment records", "SSH hardening config"],
        "commands": [
            "# SSH hardening check:\ngrep -E 'PermitRootLogin|PasswordAuth|PubkeyAuth|Protocol|MaxAuthTries|AllowUsers' /etc/ssh/sshd_config",
            "# Enforce key-only auth (add to sshd_config):\necho -e 'PasswordAuthentication no\\nPermitRootLogin no\\nMaxAuthTries 3' | sudo tee -a /etc/ssh/sshd_config && sudo sshd -t && sudo systemctl reload sshd",
            "# Active remote sessions:\nwho -a; last | head -20",
            "# OpenVPN/WireGuard status:\nsudo systemctl status openvpn wg-quick@wg0 2>/dev/null",
        ],
        "suggestion": "Enforce MFA for all remote access (VPN + SSH). Disable SSH password auth entirely. Use short-lived certificates (HashiCorp Vault SSH CA) where possible. Log all remote sessions to SIEM.",
    },
    "ac-18": {
        "artifacts": ["Wireless policy", "AP inventory with encryption type", "Wireless network scan results"],
        "commands": [
            "# List wireless interfaces:\nip link show | grep -i wireless; iwconfig 2>/dev/null",
            "# Check for rogue APs (requires airodump-ng):\nsudo airodump-ng wlan0 --write /tmp/ap-scan --output-format csv 2>/dev/null; cat /tmp/ap-scan-01.csv 2>/dev/null | head -20",
            "# Verify WPA3/WPA2 enforcement (hostapd):\ngrep -E 'wpa|rsn' /etc/hostapd/hostapd.conf 2>/dev/null",
        ],
        "suggestion": "Enforce WPA3-Enterprise or WPA2-Enterprise (802.1X). Conduct quarterly rogue AP scans. Separate guest wireless on isolated VLAN with no internal access.",
    },

    # ── AT — Awareness and Training ─────────────────────────────────────────
    "at-1": {
        "artifacts": ["Security Awareness and Training Policy", "Training procedures", "Policy review log"],
        "commands": [],
        "suggestion": "Policy must address frequency (annual minimum), roles, content requirements, and tracking. Use an LMS for automated enrollment and completion tracking.",
    },
    "at-2": {
        "artifacts": ["Training completion records (all users)", "Training curriculum outline", "Acknowledgment forms"],
        "commands": [
            "# If using SCORM/LMS, export completion report from admin console.",
            "# Quick headcount: users vs trained users:\nwc -l < <(getent passwd | awk -F: '$3>=1000') # total users\n# Compare to LMS export count",
        ],
        "suggestion": "Require annual security awareness training for ALL personnel before system access is granted. Track completion in LMS. Provide phishing simulation quarterly. Document 100% completion rate.",
    },

    # ── AU — Audit and Accountability ───────────────────────────────────────
    "au-2": {
        "artifacts": ["Auditable events list (approved by ISSO)", "Audit policy documentation"],
        "commands": [
            "# Check auditd rules:\nsudo auditctl -l",
            "# View current audit config:\ncat /etc/audit/auditd.conf",
            "# View audit rules files:\nls -la /etc/audit/rules.d/; cat /etc/audit/rules.d/*.rules 2>/dev/null",
        ],
        "suggestion": "Implement CIS Benchmark auditd rules. At minimum audit: login/logout, privilege escalation, file access to /etc, /bin, /sbin, account changes, and network config changes.",
    },
    "au-3": {
        "artifacts": ["Sample audit log entries showing required fields", "Log format specification"],
        "commands": [
            "# Verify log format contains required fields (type, time, uid, pid, exe, result):\nausearch -ts today -i | head -30",
            "# Test login event logging:\ngrep -E 'session opened|session closed|FAILED' /var/log/auth.log | tail -20",
        ],
        "suggestion": "NIST requires logs to include: type, date/time, user/subject, event type, where it occurred, and outcome (success/fail). Validate log format against this checklist.",
    },
    "au-6": {
        "artifacts": ["Audit review SOP", "Weekly review sign-off records", "Alert thresholds documentation"],
        "commands": [
            "# Search for failed auth attempts (last 24h):\nausearch -ts today -m USER_AUTH --success no -i 2>/dev/null | tail -50",
            "# Privileged command executions today:\nausearch -ts today -m EXECVE -ui 0 -i 2>/dev/null | grep -v 'cron\\|systemd' | tail -50",
            "# Failed sudo attempts:\ngrep 'sudo:.*NOT in sudoers\\|sudo:.*authentication failure' /var/log/auth.log | tail -30",
        ],
        "suggestion": "Configure automated alerting in your SIEM (Wazuh/Splunk/ELK) for failed logins >5/hour, any root login, privilege escalation, and log deletion. Document weekly review with sign-off.",
    },
    "au-9": {
        "artifacts": ["Log server configuration", "Access control list for log files", "Log integrity verification evidence"],
        "commands": [
            "# Check audit log permissions:\nls -la /var/log/audit/audit.log",
            "# Verify only root/auditd can write:\nstat /var/log/audit/audit.log | grep Access",
            "# Check if logs are forwarded to central server:\ngrep -E 'remote_server|server' /etc/audit/auditd.conf /etc/rsyslog.conf 2>/dev/null",
            "# Protect audit logs from deletion (immutable flag):\nsudo chattr +a /var/log/audit/audit.log",
        ],
        "suggestion": "Forward all audit logs to a centralized, write-once SIEM immediately on generation. Apply +a (append-only) flag to local logs. Restrict audit log read access to audit admins only.",
    },
    "au-11": {
        "artifacts": ["Log retention policy", "Log storage capacity evidence", "Archival configuration"],
        "commands": [
            "# Check auditd log retention config:\ngrep -E 'max_log_file|num_logs|max_log_file_action' /etc/audit/auditd.conf",
            "# Current log directory size and oldest log:\ndu -sh /var/log/audit/ && ls -lht /var/log/audit/ | tail -5",
            "# Logrotate config:\ncat /etc/logrotate.d/audit 2>/dev/null || echo 'No logrotate config for audit'",
        ],
        "suggestion": "NIST recommends 3-year retention for moderate impact systems. Configure auditd with max_log_file_action=ROTATE, num_logs=52 (weekly rotations). Archive to immutable cold storage (S3 Glacier / tape) for long-term.",
    },
    "au-12": {
        "artifacts": ["auditd service status", "Audit rules file", "Evidence of events being captured"],
        "commands": [
            "# Start and enable auditd:\nsudo systemctl enable --now auditd",
            "# Install recommended CIS audit rules:\nsudo apt install auditd audispd-plugins -y\nwget -O /etc/audit/rules.d/cis.rules https://raw.githubusercontent.com/Neo23x0/auditd/master/audit.rules\nauditctl -R /etc/audit/rules.d/cis.rules",
            "# Verify recording:\nausearch -ts recent -m LOGIN -i | head -10",
            "# Check audit daemon status:\nservice auditd status; auditctl -s",
        ],
        "suggestion": "Install auditd and apply CIS L2 audit rules. Ensure auditd.service is enabled and running. Rules must be immutable (-e 2) in production to prevent tampering.",
    },

    # ── CA — Assessment, Authorization, and Monitoring ──────────────────────
    "ca-1": {
        "artifacts": ["Assessment, Authorization and Monitoring Policy", "Procedures document"],
        "commands": [],
        "suggestion": "Policy must address the frequency and scope of security assessments, authorization to operate (ATO) lifecycle, and continuous monitoring requirements.",
    },
    "ca-2": {
        "artifacts": ["Security Assessment Plan (SAP)", "Security Assessment Report (SAR)", "Assessor credentials/qualifications"],
        "commands": [],
        "suggestion": "Commission annual third-party or independent security assessment. SAR must document test methods, findings, risks, and remediation recommendations.",
    },
    "ca-3": {
        "artifacts": ["Interconnection agreements (ISAs/MOUs)", "Data flow diagram showing external connections", "Port/protocol/service matrix"],
        "commands": [
            "# External connections established from this host:\nss -tnp state established | grep -v '127.0.0\\|::1' | sort -u",
            "# External DNS lookups (DNS cache):\nnscd -g 2>/dev/null | grep 'hosts cache\\|calls' || cat /var/cache/nscd/hosts 2>/dev/null | strings | grep -v localhost | head -20",
        ],
        "suggestion": "Document every external system connection in a formal ISA. Include: data classification, ports/protocols, security controls on both ends, responsible party, and annual review date.",
    },
    "ca-5": {
        "artifacts": ["Plan of Action and Milestones (POA&M)", "Vulnerability tracking records", "Remediation milestone dates"],
        "commands": [
            "# Export open findings from vulnerability scanner:\n# Nessus: Reports > Export to CSV\n# OpenVAS: Reports > Download > CSV Results",
        ],
        "suggestion": "Maintain a live POA&M tracking all open findings. Each item must have: finding source, risk level, responsible party, planned completion date, and status. Review monthly.",
    },
    "ca-6": {
        "artifacts": ["Authorization to Operate (ATO) letter", "Risk acceptance memo", "Security Plan signed by AO"],
        "commands": [],
        "suggestion": "Obtain formal ATO from Authorizing Official before going live. Document residual risks in a Risk Acceptance memo. Schedule reauthorization at minimum every 3 years or on significant change.",
    },
    "ca-7": {
        "artifacts": ["Continuous monitoring strategy", "Automated scanning evidence", "Metrics dashboard screenshots"],
        "commands": [
            "# Run automated vulnerability scan:\nsudo openvas-start 2>/dev/null || sudo lynis audit system",
            "# Wazuh agent status:\nsudo /var/ossec/bin/agent_control -ls",
            "# Quick hardening check:\nsudo lynis audit system --quick 2>/dev/null | tail -30",
        ],
        "suggestion": "Implement automated continuous monitoring: daily vulnerability scans, real-time SIEM alerting, monthly configuration compliance checks. Document metrics (patch %, open vulns, MTTD/MTTR).",
    },

    # ── CM — Configuration Management ───────────────────────────────────────
    "cm-2": {
        "artifacts": ["Baseline configuration document", "Approved configuration checklist (CIS Benchmark)", "Deviation justification records"],
        "commands": [
            "# CIS benchmark assessment:\nsudo docker run --rm --pid=host --userns=host --cap-add audit_control \\\n  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \\\n  -v /etc:/etc:ro -v /usr/bin/containerd:/usr/bin/containerd:ro \\\n  docker/docker-bench-security 2>/dev/null | head -50",
            "# Linux baseline snapshot:\nsudo lynis audit system 2>/dev/null | grep '\\[WARNING\\]\\|\\[SUGGESTION\\]' | head -30",
            "# Export current package versions:\ndpkg -l > /tmp/baseline-packages-$(date +%F).txt",
        ],
        "suggestion": "Create a formal baseline using the applicable CIS Benchmark. Document every deviation with a risk justification. Store baseline in version control and check drift quarterly.",
    },
    "cm-6": {
        "artifacts": ["Configuration settings documentation", "SCAP/STIG compliance scan results", "Automated compliance check evidence"],
        "commands": [
            "# STIG check (OpenSCAP):\nsudo oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_stig \\\n  --results /tmp/stig-results.xml \\\n  /usr/share/xml/scap/ssg/content/ssg-ubuntu2004-ds.xml 2>/dev/null | tail -20",
            "# Check key hardening settings:\ngrep -E 'PASS_MAX_DAYS|PASS_MIN_DAYS|PASS_WARN' /etc/login.defs",
            "# Kernel hardening:\nsysctl -a 2>/dev/null | grep -E 'net.ipv4.ip_forward|kernel.randomize_va_space|kernel.dmesg_restrict'",
        ],
        "suggestion": "Apply CIS L2 or STIG configurations. Automate compliance checking with OpenSCAP or Chef InSpec. Treat configuration as code (Ansible playbooks) and enforce via CI/CD pipeline.",
    },
    "cm-7": {
        "artifacts": ["Approved services/ports list", "Disabled services documentation", "Firewall ruleset"],
        "commands": [
            "# All running services:\nsystemctl list-units --type=service --state=running --no-pager",
            "# All listening ports:\nss -tulnp | sort -k5",
            "# Disable a service:\nsudo systemctl disable --now <service_name>",
            "# Installed but unnecessary packages:\nsudo deborphan 2>/dev/null || dpkg --get-selections | grep -v deinstall | awk '{print $1}' > /tmp/installed.txt",
        ],
        "suggestion": "Create a whitelist of approved services and ports. Disable and remove all others. Use AppArmor/SELinux profiles to restrict what remaining services can do.",
    },
    "cm-8": {
        "artifacts": ["System component inventory (hardware/software)", "Automated discovery scan results", "License compliance records"],
        "commands": [
            "# Hardware inventory:\nsudo dmidecode -t system -t baseboard -t processor -t memory 2>/dev/null | grep -E 'Product|Manufacturer|Version|Size'",
            "# Software inventory:\ndpkg -l | awk '{print $2,$3}' | sort > /tmp/sw-inventory-$(date +%F).txt",
            "# Network device discovery:\nnmap -sn 192.168.0.0/24 -oN /tmp/network-inventory.txt 2>/dev/null | grep 'Nmap scan\\|report for'",
        ],
        "suggestion": "Maintain a live CMDB. Automate discovery with Nmap + Ansible facts collection. Reconcile monthly. Every component must have owner, OS version, patch level, and business function.",
    },

    # ── CP — Contingency Planning ────────────────────────────────────────────
    "cp-2": {
        "artifacts": ["Contingency Plan (CP) document", "Business Impact Analysis (BIA)", "Annual test results"],
        "commands": [],
        "suggestion": "Contingency Plan must address: BIA results, recovery objectives (RTO/RPO), notification procedures, recovery procedures, and reconstitution steps. Test annually — tabletop at minimum.",
    },
    "cp-9": {
        "artifacts": ["Backup policy", "Automated backup job logs", "Restoration test records"],
        "commands": [
            "# Verify latest backup exists and is recent:\nls -lht /backup/ 2>/dev/null | head -10; ls -lht /mnt/backup/ 2>/dev/null | head -10",
            "# Check backup service status:\nsystemctl status restic bacula bareos duplicati 2>/dev/null | grep -E 'Active:|backup'",
            "# Backup all critical data (example with restic):\nrestic -r /mnt/backup/myrepo backup /etc /var/lib/postgresql /home --verbose",
            "# Test restore (non-destructive):\nrestic -r /mnt/backup/myrepo restore latest --target /tmp/restore-test --include /etc/passwd",
        ],
        "suggestion": "Implement automated daily backups with 90-day retention. Test restoration quarterly — document RTO/RPO achievement. Use 3-2-1 rule: 3 copies, 2 media types, 1 offsite.",
    },
    "cp-10": {
        "artifacts": ["System recovery procedures", "Recovery time objective (RTO) evidence", "Post-incident recovery test log"],
        "commands": [
            "# Create system image (for bare-metal recovery):\nsudo clonezilla-live 2>/dev/null || sudo dd if=/dev/sda | gzip > /backup/disk-$(date +%F).img.gz",
        ],
        "suggestion": "Document exact step-by-step recovery procedures. Conduct annual full recovery exercises. Verify you can meet declared RTO. Store recovery media and procedures offline.",
    },

    # ── IA — Identification and Authentication ───────────────────────────────
    "ia-2": {
        "artifacts": ["MFA enrollment records", "Authentication policy", "Privileged user auth exception list"],
        "commands": [
            "# Check PAM MFA (TOTP/FIDO2):\ngrep -r 'pam_google_authenticator\\|pam_u2f\\|pam_oath' /etc/pam.d/",
            "# SSH MFA via AuthenticationMethods:\ngrep 'AuthenticationMethods\\|ChallengeResponse' /etc/ssh/sshd_config",
            "# List users without MFA (if using Google Auth):\nfor u in $(cut -d: -f1 /etc/passwd); do [ -f /home/$u/.google_authenticator ] || echo \"No MFA: $u\"; done",
        ],
        "suggestion": "Enforce MFA for ALL privileged access and all network access. Use FIDO2/WebAuthn where possible (phishing-resistant). Enroll 100% of privileged users before go-live.",
    },
    "ia-5": {
        "artifacts": ["Password policy documentation", "PAM/AD password policy config", "Initial credential distribution procedures"],
        "commands": [
            "# Check password complexity policy:\ncat /etc/pam.d/common-password | grep -E 'pam_pwquality|pam_cracklib|minlen|ucredit|dcredit'",
            "# Check /etc/security/pwquality.conf:\ncat /etc/security/pwquality.conf 2>/dev/null | grep -v '^#\\|^$'",
            "# Enforce strong passwords (add to /etc/security/pwquality.conf):\nsudo tee -a /etc/security/pwquality.conf <<'EOF'\\nminlen = 15\\nminclass = 3\\ndictcheck = 1\\nusercheck = 1\\nEOF",
            "# Check password age settings:\ngrep -E 'PASS_MAX|PASS_MIN|PASS_WARN' /etc/login.defs",
        ],
        "suggestion": "Enforce: min 15 chars, 3 character classes, no dictionary words, no username. Max age 365 days. Initial passwords must be changed on first use. Use a PAM pwquality policy enforced at the OS level.",
    },
    "ia-6": {
        "artifacts": ["Authentication UI configuration", "Feedback obscuration testing evidence"],
        "commands": [
            "# Verify SSH does not reveal valid usernames:\ngrep 'IgnoreUserKnownHosts\\|PermitUserEnvironment' /etc/ssh/sshd_config",
            "# Check web app login for user enumeration (manual):\n# POST /login with valid user/wrong pass → note response timing/message\n# POST /login with invalid user/wrong pass → compare timing/message",
        ],
        "suggestion": "Ensure login failure messages are generic ('Invalid credentials' not 'Invalid password' or 'User not found'). Enforce consistent response timing to prevent user enumeration.",
    },
    "ia-8": {
        "artifacts": ["Non-organizational user authentication procedures", "PIV/CAC acceptance documentation"],
        "commands": [
            "# Check for PIV/OCSP configuration:\ngrep -r 'OCSPEnable\\|OCSPDefaultResponder\\|SSLVerifyClient' /etc/apache2/ /etc/nginx/ 2>/dev/null",
        ],
        "suggestion": "For federal systems, require PIV/CAC for all non-organizational users with privileged access. Document exceptions with compensating controls.",
    },

    # ── IR — Incident Response ───────────────────────────────────────────────
    "ir-1": {
        "artifacts": ["Incident Response Policy", "IR Procedures", "Annual review evidence"],
        "commands": [],
        "suggestion": "IR policy must define incident categories, reporting chain, escalation thresholds, containment authority, and legal/regulatory notification requirements.",
    },
    "ir-2": {
        "artifacts": ["IR training completion records", "Tabletop exercise reports", "Annual test schedule"],
        "commands": [],
        "suggestion": "Train all IR team members annually. Conduct quarterly tabletop exercises covering top scenarios (ransomware, data breach, insider threat). Document lessons learned.",
    },
    "ir-4": {
        "artifacts": ["Incident handling procedures", "Incident tickets/reports", "Containment decision log"],
        "commands": [
            "# Isolate a compromised host (preserve evidence):\nsudo iptables -I INPUT -j DROP; sudo iptables -I OUTPUT -j DROP  # Block all except management IP",
            "# Capture running process evidence before shutdown:\nsudo ps auxf > /evidence/processes-$(date +%F-%T).txt\nsudo netstat -tulnp >> /evidence/netstat-$(date +%F-%T).txt\nsudo lsof -nP >> /evidence/lsof-$(date +%F-%T).txt",
            "# Memory dump (requires LiME kernel module):\nsudo insmod lime-$(uname -r).ko \"path=/evidence/ram.lime format=lime\" 2>/dev/null",
        ],
        "suggestion": "Develop playbooks for each incident category. Each playbook must include: detection, containment, eradication, recovery, and lessons-learned steps with specific commands.",
    },
    "ir-5": {
        "artifacts": ["Incident tracking log (ticket system export)", "Incident summary reports"],
        "commands": [
            "# List failed auth attempts (potential incidents):\nfaillock --user root 2>/dev/null; grep 'Failed password' /var/log/auth.log | awk '{print $1,$2,$3,$9,$11}' | sort | uniq -c | sort -rn | head -20",
        ],
        "suggestion": "Maintain a centralized incident tracker (Jira/ServiceNow). Every security event must be logged, triaged, and dispositioned. Export quarterly summary showing MTTD and MTTR metrics.",
    },
    "ir-6": {
        "artifacts": ["Incident reporting SOP", "US-CERT/CISA reporting records", "Stakeholder notification templates"],
        "commands": [],
        "suggestion": "Federal systems: report incidents to US-CERT within 1 hour of discovery (major incidents). Document notification chain and timing in incident report. Maintain templates for rapid notification.",
    },

    # ── MA — Maintenance ─────────────────────────────────────────────────────
    "ma-2": {
        "artifacts": ["Maintenance schedule and log", "Change tickets for maintenance windows", "Remote maintenance session logs"],
        "commands": [
            "# Log all maintenance activities:\nwho -a | tee -a /var/log/maintenance.log",
            "# Check pending updates:\napt list --upgradable 2>/dev/null | grep -c upgradable",
        ],
        "suggestion": "Log all maintenance activities in a maintenance register: date, who performed, what was done, authorization reference, and outcome. Review logs after each maintenance window.",
    },
    "ma-4": {
        "artifacts": ["Remote maintenance policy", "VPN/jump server logs", "Multi-party authorization records"],
        "commands": [
            "# Log all SSH sessions (verify SSH session recording is enabled):\ngrep -E 'session opened|session closed|sshd' /var/log/auth.log | tail -30",
            "# Enable SSH session recording with script:\n# Add to /etc/ssh/sshrc: script -q -f /var/log/sessions/$(date +%F)-$(whoami)-$$.log",
        ],
        "suggestion": "All remote maintenance must go through an audited jump server. Enable full session recording (script command or Teleport). Require dual authorization for remote maintenance of production systems.",
    },

    # ── MP — Media Protection ────────────────────────────────────────────────
    "mp-2": {
        "artifacts": ["Media access control procedures", "Removable media policy", "Authorized user list for media access"],
        "commands": [
            "# Block USB storage devices:\necho 'install usb-storage /bin/true' | sudo tee /etc/modprobe.d/disable-usb-storage.conf\nsudo update-initramfs -u",
            "# Check if USB storage is blocked:\ncat /etc/modprobe.d/disable-usb-storage.conf 2>/dev/null",
        ],
        "suggestion": "Block USB storage via kernel module blacklist. If USB is required, implement DLP solution with device whitelisting by serial number. Log all media access.",
    },
    "mp-6": {
        "artifacts": ["Media sanitization procedures", "Sanitization log/records", "Certificate of destruction for retired hardware"],
        "commands": [
            "# Secure wipe a disk (DoD 5220.22-M, 3-pass):\nsudo shred -v -n 3 -z /dev/sdX  # replace sdX with target device",
            "# NIST 800-88 compliant SSD purge (if supported):\nsudo hdparm --security-erase-enhanced /dev/sdX 2>/dev/null",
            "# Verify disk is wiped:\nsudo hexdump -C /dev/sdX | head -5",
        ],
        "suggestion": "For HDDs: NIST 800-88 clear (1-pass overwrite). For SSDs/NVMe: cryptographic erase or physical destruction. Document all sanitization with serial number, method, date, and witness signature.",
    },

    # ── PE — Physical and Environmental Protection ───────────────────────────
    "pe-1": {
        "artifacts": ["Physical Security Policy", "Procedures document"],
        "commands": [],
        "suggestion": "Policy must address: facility access, visitor management, equipment protection, and environmental monitoring. Review annually.",
    },
    "pe-2": {
        "artifacts": ["Physical access authorization list", "Access control system logs", "Badge issuance records"],
        "commands": [],
        "suggestion": "Maintain a current access authorization list. Review and recertify quarterly. Remove access within 24 hours of personnel departure. Export badge access logs to SIEM.",
    },
    "pe-3": {
        "artifacts": ["Physical access control system (PACS) configuration", "Visitor log", "Access log for 90 days"],
        "commands": [],
        "suggestion": "Use electronic PACS with individual credentials (not shared PINs). Export access logs to centralized SIEM for anomaly detection. Lock server racks with logged electronic locks.",
    },

    # ── PL — Planning ────────────────────────────────────────────────────────
    "pl-2": {
        "artifacts": ["System Security Plan (SSP)", "Architecture diagram", "ATO signature page"],
        "commands": [],
        "suggestion": "SSP must be complete (all controls addressed), reviewed annually, updated on significant changes, and signed by the System Owner and AO. Version control the SSP in a document management system.",
    },

    # ── RA — Risk Assessment ─────────────────────────────────────────────────
    "ra-1": {
        "artifacts": ["Risk Assessment Policy", "Procedures", "Annual review log"],
        "commands": [],
        "suggestion": "Policy must address risk assessment frequency, methodology, tools, and integration with the risk management framework.",
    },
    "ra-3": {
        "artifacts": ["Risk Assessment Report", "Risk register", "Threat modeling artifacts"],
        "commands": [
            "# Run automated vulnerability assessment:\nsudo openvas-cli -h 127.0.0.1 -u admin -w admin -T html -o /tmp/va-report.html --start-task $(openvas-cli -h 127.0.0.1 -u admin -w admin --get-tasks | grep 'Full.*Fast' | grep -oP '(?<=task_id=)[^ ]+') 2>/dev/null",
            "# Nessus-style local vulnerability check:\nsudo lynis audit system 2>&1 | grep -E 'WARNING|SUGGESTION|hardening_index'",
        ],
        "suggestion": "Conduct annual risk assessments using NIST SP 800-30. Document threats, vulnerabilities, likelihood, impact, and risk level. Update risk register after every significant change or incident.",
    },
    "ra-5": {
        "artifacts": ["Vulnerability scan results (authenticated)", "Remediation tracking records", "Scan schedule documentation"],
        "commands": [
            "# Authenticated local scan:\nsudo apt install -y openvas 2>/dev/null && sudo openvas-setup 2>/dev/null",
            "# Fast local vulnerability check:\nsudo lynis audit system --tests-from-group malware,authentication,networking,filesystems 2>/dev/null | grep -E 'FOUND|WARNING' | head -30",
            "# Check for CVEs in installed packages:\ncurl -s https://services.nvd.nist.gov/rest/json/cves/2.0?keyword=$(dpkg -l | awk 'NR>5{print $2}' | head -1) 2>/dev/null | python3 -m json.tool | grep 'id\\|description' | head -20",
        ],
        "suggestion": "Run authenticated vulnerability scans monthly. Patch Critical/High findings within 30 days, Medium within 90 days. Document exception/acceptance process for findings that cannot be remediated.",
    },

    # ── SA — System and Services Acquisition ────────────────────────────────
    "sa-3": {
        "artifacts": ["SDLC policy", "Security requirements in project plans", "Security gate review records"],
        "commands": [
            "# SAST scan (Semgrep):\nsemgrep --config=auto /path/to/source 2>/dev/null | grep -E 'ERROR|WARNING' | head -20",
            "# Dependency vulnerability check:\nnpm audit 2>/dev/null || pip-audit 2>/dev/null || safety check 2>/dev/null",
        ],
        "suggestion": "Integrate security into every SDLC phase: requirements, design (threat modeling), implementation (SAST), testing (DAST/pen test), and deployment (config review). Gate releases on security sign-off.",
    },
    "sa-4": {
        "artifacts": ["Contract security requirements", "Vendor security assessments", "SLA documents with security clauses"],
        "commands": [],
        "suggestion": "Include security requirements in all acquisition contracts: data handling, incident reporting obligations, right-to-audit, background check requirements, and compliance certifications (FedRAMP, SOC2).",
    },
    "sa-11": {
        "artifacts": ["SAST/DAST scan reports", "Penetration test reports", "Code review records"],
        "commands": [
            "# DAST scan with OWASP ZAP:\ndocker run -t owasp/zap2docker-stable zap-baseline.py -t https://your-app.example.com 2>/dev/null | tail -30",
            "# SAST with Semgrep:\ndocker run --rm -v \"$(pwd):/src\" returntocorp/semgrep --config=auto /src 2>/dev/null | grep 'findings' | head -10",
            "# Secret scanning:\ngit secrets --scan 2>/dev/null || trufflehog git file://. 2>/dev/null | head -30",
        ],
        "suggestion": "Require pre-production penetration testing for all major releases. Automate SAST in CI/CD pipeline (block merge on Critical findings). Conduct DAST quarterly against production.",
    },

    # ── SC — System and Communications Protection ───────────────────────────
    "sc-7": {
        "artifacts": ["Network topology diagram", "Firewall ruleset export", "DMZ architecture documentation"],
        "commands": [
            "# Full firewall ruleset:\nsudo iptables-save 2>/dev/null || sudo nft list ruleset",
            "# UFW full status:\nsudo ufw status verbose",
            "# External connections from this host:\nss -tnp state established | grep -vE '127.0.0|::1|10\\.|172\\.1[6-9]\\.|172\\.2[0-9]\\.|192\\.168\\.'",
            "# Check default drop policies:\nsudo iptables -L | grep 'Chain.*policy'",
        ],
        "suggestion": "Implement deny-by-default perimeter firewall. Place internet-facing services in DMZ (separate VLAN/subnet). Document all firewall rules with justification and owner. Review ruleset quarterly.",
    },
    "sc-8": {
        "artifacts": ["TLS configuration evidence", "Certificate inventory", "Network scan showing encryption in transit"],
        "commands": [
            "# Check TLS config for web services:\nnmap --script ssl-enum-ciphers -p 443 <target> 2>/dev/null | grep -E 'TLSv|strength|cipher'",
            "# testssl.sh full check:\ndocker run --rm drwetter/testssl.sh https://<target> 2>/dev/null | grep -E 'WARN|CRITICAL|OK' | head -30",
            "# Check certificate expiry:\necho | openssl s_client -servername <host> -connect <host>:443 2>/dev/null | openssl x509 -noout -dates",
            "# Disable TLS 1.0/1.1 in nginx:\ngrep 'ssl_protocols' /etc/nginx/nginx.conf || echo 'ssl_protocols TLSv1.2 TLSv1.3;' | sudo tee -a /etc/nginx/conf.d/ssl.conf",
        ],
        "suggestion": "Enforce TLS 1.2 minimum (TLS 1.3 preferred). Disable TLS 1.0/1.1 and all weak ciphers (RC4, 3DES, NULL). Enable HSTS. Use automated certificate management (Let's Encrypt/ACME). A+ on SSL Labs.",
    },
    "sc-12": {
        "artifacts": ["Cryptographic key management policy", "Key inventory", "Key ceremony records"],
        "commands": [
            "# List SSH host keys:\nls -la /etc/ssh/ssh_host_*",
            "# List SSL certificates and keys:\nfind /etc/ssl /etc/pki /etc/letsencrypt -name '*.pem' -o -name '*.key' 2>/dev/null | xargs ls -la 2>/dev/null",
            "# GPG key inventory:\ngpg --list-keys 2>/dev/null",
        ],
        "suggestion": "Implement formal key management: inventory all crypto keys, document custodians, set expiry, and document rotation procedures. Use HSM for key protection in high-impact systems.",
    },
    "sc-13": {
        "artifacts": ["Cryptographic standards documentation", "FIPS 140-2/3 validation evidence"],
        "commands": [
            "# Check if FIPS mode is enabled:\ncat /proc/sys/crypto/fips_enabled 2>/dev/null",
            "# Enable FIPS mode (Ubuntu):\nsudo ua enable fips 2>/dev/null || sudo apt install -y linux-fips 2>/dev/null",
            "# Verify OpenSSL FIPS mode:\nopenssl md5 /dev/null 2>&1 | grep -i 'error\\|not allowed\\|disabled'",
        ],
        "suggestion": "Use FIPS 140-2/3 validated cryptographic modules for all encryption. For federal systems, enable FIPS mode at the OS level. Document all cryptographic algorithm usage.",
    },
    "sc-20": {
        "artifacts": ["DNSSEC configuration", "DNS zone signing evidence", "Recursive resolver DNSSEC validation"],
        "commands": [
            "# Check DNSSEC for your domain:\ndig +dnssec your-domain.com | grep -E 'RRSIG|AD|DNSKEY'",
            "# Verify DNSSEC is validating:\ndig @8.8.8.8 +dnssec bogusdomain.dnssec.fail | grep -E 'SERVFAIL|AD'",
            "# Check BIND DNSSEC config:\ngrep -E 'dnssec|validation' /etc/bind/named.conf* 2>/dev/null",
        ],
        "suggestion": "Enable DNSSEC signing for all authoritative zones. Configure recursive resolvers to validate DNSSEC. Add DS records at registrar. Monitor zone signing key (ZSK) and key signing key (KSK) rotation.",
    },
    "sc-28": {
        "artifacts": ["Encryption at rest policy", "LUKS/BitLocker configuration evidence", "Database encryption evidence"],
        "commands": [
            "# Check disk encryption status:\nlsblk -o name,type,fstype,mountpoint,UUID | grep -i crypt",
            "# Check LUKS encrypted volumes:\nsudo dmsetup ls --target crypt 2>/dev/null",
            "# Verify a specific volume is LUKS encrypted:\nsudo cryptsetup isLuks /dev/sda1 && echo 'LUKS encrypted' || echo 'NOT encrypted'",
            "# Encrypt new volume with LUKS (AES-256-XTS):\nsudo cryptsetup luksFormat --type luks2 --cipher aes-xts-plain64 --key-size 512 --hash sha256 /dev/sdX",
            "# PostgreSQL column encryption:\n# ALTER TABLE users ALTER COLUMN ssn TYPE bytea USING pgp_sym_encrypt(ssn::text, 'key');",
        ],
        "suggestion": "Encrypt all storage containing sensitive data at rest using LUKS (Linux) or BitLocker (Windows). For databases, implement TDE or column-level encryption for PII/sensitive fields. Document encryption key storage.",
    },

    # ── SI — System and Information Integrity ───────────────────────────────
    "si-2": {
        "artifacts": ["Patch management policy", "Patch scan results", "Patching SLA compliance report"],
        "commands": [
            "# Check for security updates:\napt list --upgradable 2>/dev/null | grep -i security",
            "# View available security patches:\nsudo unattended-upgrades --dry-run 2>/dev/null | head -20",
            "# Enable automatic security updates:\nsudo dpkg-reconfigure --priority=low unattended-upgrades",
            "# Apply security updates immediately:\nsudo apt-get -s upgrade 2>/dev/null | grep 'Inst.*security'  # dry run first\nsudo apt-get upgrade -y",
            "# Check kernel version vs latest:\nuname -r; apt-cache policy linux-image-generic | head -3",
        ],
        "suggestion": "Enable unattended-upgrades for automatic security patching. Critical/High CVEs: patch within 15 days. Medium: 30 days. Low: 90 days. Document exceptions with risk acceptance. Report patch compliance monthly.",
    },
    "si-3": {
        "artifacts": ["Anti-malware deployment evidence", "Scan logs/reports", "Signature update evidence"],
        "commands": [
            "# Install and run ClamAV:\nsudo apt install -y clamav clamav-daemon && sudo freshclam && sudo clamscan -r --infected /etc /var /home 2>/dev/null | tail -20",
            "# Check ClamAV service:\nsudo systemctl status clamav-freshclam clamav-daemon",
            "# Rootkit scan:\nsudo rkhunter --check --skip-keypress 2>/dev/null | grep -E 'Warning|Found|Suspicious'",
            "# AIDE file integrity check:\nsudo aide --check 2>/dev/null | grep -E 'changed|added|removed' | head -20",
        ],
        "suggestion": "Deploy ClamAV with daily signature updates and real-time scanning (on-access). Add AIDE for file integrity monitoring of /bin, /sbin, /usr/bin, /etc. Configure rootkit scanner (rkhunter) to run weekly.",
    },
    "si-4": {
        "artifacts": ["IDS/IPS deployment evidence", "SIEM alert configuration", "Monitoring coverage diagram"],
        "commands": [
            "# Wazuh agent status:\nsudo /var/ossec/bin/ossec-control status 2>/dev/null || sudo systemctl status wazuh-agent",
            "# Suricata IDS status:\nsudo systemctl status suricata; sudo tail -f /var/log/suricata/fast.log 2>/dev/null | head -20",
            "# Real-time auth monitoring:\ntail -f /var/log/auth.log | grep -E 'Failed|Invalid|error'",
            "# Check Fail2ban is running:\nsudo fail2ban-client status; sudo fail2ban-client status sshd",
        ],
        "suggestion": "Deploy host-based IDS (Wazuh/OSSEC) on all endpoints. Deploy network-based IDS (Suricata/Snort) at network boundaries. Centralize all alerts in SIEM. Configure real-time alerting for high-severity events.",
    },
    "si-5": {
        "artifacts": ["Security alert subscription evidence", "Patch watch list", "Advisory tracking records"],
        "commands": [
            "# Subscribe to NVD notifications (add to cron):\n# curl -s 'https://services.nvd.nist.gov/rest/json/cves/2.0?pubStartDate=$(date -d yesterday +%Y-%m-%dT%H:%M:%S)' | python3 -m json.tool | grep 'id\\|severity'",
            "# Check CISA KEV (Known Exploited Vulnerabilities):\ncurl -s https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json | python3 -c \"import json,sys; d=json.load(sys.stdin); [print(v['cveID'],v['shortDescription'][:60]) for v in d['vulnerabilities'][:10]]\" 2>/dev/null",
        ],
        "suggestion": "Subscribe to vendor security bulletins, US-CERT/CISA alerts, and NVD CVE notifications. Assign a team member to review advisories daily. Track advisories to affected systems in your vulnerability register.",
    },
    "si-7": {
        "artifacts": ["File integrity monitoring (FIM) configuration", "Baseline hash database", "FIM alert logs"],
        "commands": [
            "# Install and initialize AIDE:\nsudo apt install -y aide && sudo aideinit && sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db",
            "# Run integrity check:\nsudo aide --check 2>/dev/null | tee /var/log/aide/aide-$(date +%F).log | tail -20",
            "# Add daily AIDE check to cron:\necho '0 2 * * * root /usr/bin/aide --check | mail -s \"AIDE report $(hostname) $(date +%F)\" security@example.com' | sudo tee /etc/cron.d/aide",
            "# Verify critical binary hashes:\nsha256sum /bin/ls /bin/bash /usr/bin/ssh /usr/bin/sudo | tee /root/critical-hashes.txt",
        ],
        "suggestion": "Implement AIDE or Tripwire for FIM of all system directories (/bin, /sbin, /etc, /boot). Initialize baseline after clean install. Run daily checks and alert on any unexpected changes. Store baseline offline.",
    },

    # ── SR — Supply Chain Risk Management ───────────────────────────────────
    "sr-1": {
        "artifacts": ["Supply Chain Risk Management Policy", "Vendor assessment procedures"],
        "commands": [],
        "suggestion": "Policy must address vendor vetting, software provenance verification, dependency management, and component tracking throughout the system lifecycle.",
    },
    "sr-3": {
        "artifacts": ["Approved supplier list", "SBOM (Software Bill of Materials)", "Vendor security questionnaires"],
        "commands": [
            "# Generate SBOM with Syft:\ndocker run --rm anchore/syft:latest dir:. 2>/dev/null | head -30",
            "# Check for vulnerable dependencies:\npip-audit 2>/dev/null || safety check --json 2>/dev/null | python3 -m json.tool | head -30",
            "# NPM audit:\nnpm audit --json 2>/dev/null | python3 -m json.tool | grep -E 'severity|title' | head -20",
            "# Maven dependency check:\nmvn dependency-check:check 2>/dev/null | tail -20",
        ],
        "suggestion": "Generate and maintain an SBOM for all software. Check all dependencies against NVD/OSV databases in CI/CD pipeline. Require Tier 1 vendors to provide their own SBOMs.",
    },
}

# ---------------------------------------------------------------------------
# Family-level fallback defaults (used when no specific entry exists)
# ---------------------------------------------------------------------------
FAMILY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ac": {
        "artifacts": ["Access control policy", "Access authorization records", "Periodic access review reports"],
        "commands": [
            "# Current users and groups:\ncat /etc/passwd | awk -F: '$3>=1000{print $1,$3,$6}'; groups $(whoami)",
        ],
        "suggestion": "Document access control implementation per the control's specific requirements. Provide evidence of enforcement (logs, config exports, or automated scan results).",
    },
    "at": {
        "artifacts": ["Training completion records", "Course materials", "Training schedule"],
        "commands": [],
        "suggestion": "Provide training completion records for all personnel. Include role-specific training content and acknowledgment signatures.",
    },
    "au": {
        "artifacts": ["Audit log samples", "Audit configuration export", "Log retention evidence"],
        "commands": [
            "# Check audit service:\nsystemctl status auditd rsyslog 2>/dev/null | grep Active",
            "# Recent audit events:\nsudo ausearch -ts today -i 2>/dev/null | head -40",
        ],
        "suggestion": "Provide audit configuration exports and sample log entries demonstrating the required fields are captured.",
    },
    "ca": {
        "artifacts": ["Assessment/authorization documentation", "Control assessment records"],
        "commands": [],
        "suggestion": "Document the control assessment methodology, findings, and authorization decisions with appropriate signatures.",
    },
    "cm": {
        "artifacts": ["Configuration baseline documentation", "Change management records", "Compliance scan results"],
        "commands": [
            "# Configuration compliance baseline:\nsudo lynis audit system 2>/dev/null | grep -E 'Hardening index|WARNING' | head -20",
        ],
        "suggestion": "Provide baseline configuration documents, change management records, and automated compliance scan results.",
    },
    "cp": {
        "artifacts": ["Contingency plan", "Backup verification logs", "Recovery test results"],
        "commands": [
            "# Verify backup integrity:\nls -lht /backup/ 2>/dev/null | head -5",
        ],
        "suggestion": "Provide contingency planning documentation and evidence of regular testing. Include RTO/RPO measurement results.",
    },
    "ia": {
        "artifacts": ["Authentication policy", "Identity management system configuration", "MFA enrollment evidence"],
        "commands": [
            "# Check authentication configuration:\ngrep -E 'PasswordAuthentication|PubkeyAuth|MFA|AuthMethod' /etc/ssh/sshd_config",
        ],
        "suggestion": "Document authentication mechanisms in place. Provide configuration exports and user enrollment evidence.",
    },
    "ir": {
        "artifacts": ["Incident response plan", "Incident records/tickets", "Post-incident review reports"],
        "commands": [],
        "suggestion": "Provide IR documentation and evidence of incidents being handled per the documented procedures.",
    },
    "ma": {
        "artifacts": ["Maintenance log", "Maintenance policy", "Remote access session logs"],
        "commands": [],
        "suggestion": "Maintain a maintenance register documenting all maintenance activities with authorization references.",
    },
    "mp": {
        "artifacts": ["Media protection policy", "Media sanitization log", "Media inventory"],
        "commands": [],
        "suggestion": "Document media handling procedures and provide sanitization records for all disposed media.",
    },
    "pe": {
        "artifacts": ["Physical access control records", "Physical security policy", "Visitor logs"],
        "commands": [],
        "suggestion": "Provide physical access logs and documentation of physical security controls in place.",
    },
    "pl": {
        "artifacts": ["System Security Plan", "Architecture documentation", "Security assessment records"],
        "commands": [],
        "suggestion": "Provide complete planning documentation with current signatures and version control evidence.",
    },
    "pm": {
        "artifacts": ["Program management policy", "Organizational risk management strategy"],
        "commands": [],
        "suggestion": "Document program-level security management processes and organizational risk management decisions.",
    },
    "ps": {
        "artifacts": ["Position risk designation records", "Background check documentation", "Personnel security agreements"],
        "commands": [],
        "suggestion": "Provide documented position risk designations, background check completion records, and signed security agreements.",
    },
    "pt": {
        "artifacts": ["Privacy policy", "PII inventory", "Consent records"],
        "commands": [],
        "suggestion": "Document privacy controls, PII inventory, and consent/authorization records for data collection.",
    },
    "ra": {
        "artifacts": ["Risk assessment report", "Risk register", "Vulnerability scan results"],
        "commands": [
            "# Quick vulnerability assessment:\nsudo lynis audit system --quick 2>/dev/null | grep -E 'Hardening|WARNING|SUGGESTION' | head -20",
        ],
        "suggestion": "Provide a current risk assessment with documented threats, vulnerabilities, likelihood, impact, and risk levels.",
    },
    "sa": {
        "artifacts": ["SDLC documentation", "Security testing reports", "Vendor security assessments"],
        "commands": [],
        "suggestion": "Document security activities performed during acquisition and development phases. Provide test results and vendor assessments.",
    },
    "sc": {
        "artifacts": ["Network diagram", "Encryption configuration exports", "TLS scan results"],
        "commands": [
            "# Network boundary review:\nss -tlnp; sudo iptables -L -n | head -30",
        ],
        "suggestion": "Provide technical evidence of system and communications protection controls including configuration exports and scan results.",
    },
    "si": {
        "artifacts": ["Patch scan results", "Anti-malware logs", "File integrity monitoring reports"],
        "commands": [
            "# System integrity check:\nrpm -Va 2>/dev/null | grep -v '^....' | head -20 || dpkg --verify 2>/dev/null | head -20",
        ],
        "suggestion": "Provide evidence of system integrity monitoring, malware protection, and patch management activities.",
    },
    "sr": {
        "artifacts": ["Vendor risk assessments", "SBOM", "Supply chain security procedures"],
        "commands": [],
        "suggestion": "Document supply chain risk management activities including vendor assessments and component provenance verification.",
    },
}


def get_remediation(control_id: str) -> Dict[str, Any]:
    """
    Return remediation guidance for a control.
    Falls back to family defaults if no specific entry exists.
    """
    cid = control_id.lower().strip()
    data = REMEDIATION.get(cid, {})
    family = cid.split("-")[0] if "-" in cid else cid
    family_data = FAMILY_DEFAULTS.get(family, {})

    return {
        "artifacts":   data.get("artifacts")   or family_data.get("artifacts", []),
        "commands":    data.get("commands")     or family_data.get("commands", []),
        "suggestion":  data.get("suggestion")   or family_data.get("suggestion", ""),
    }
