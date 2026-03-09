# CISSP Domain 5: Identity and Access Management (IAM)
## Authentication Factors, Access Control Models, Federation, PAM, and Zero Trust

**CBK Domain Weight:** 13%
**Exam Focus:** Protocol mechanics, model selection, lifecycle management, and zero trust architecture principles

---

## Table of Contents

1. [IAM Fundamentals](#1-iam-fundamentals)
2. [Authentication Factors](#2-authentication-factors)
3. [Authentication Protocols](#3-authentication-protocols)
4. [Access Control Models](#4-access-control-models)
5. [Identity Federation and SSO](#5-identity-federation-and-sso)
6. [Privileged Access Management (PAM)](#6-privileged-access-management-pam)
7. [Account Lifecycle Management](#7-account-lifecycle-management)
8. [Zero Trust Principles](#8-zero-trust-principles)
9. [MFA Types and Resistance Levels](#9-mfa-types-and-resistance-levels)
10. [Directory Services](#10-directory-services)
11. [Biometrics Deep Dive](#11-biometrics-deep-dive)
12. [IAM in Cloud Environments](#12-iam-in-cloud-environments)
13. [Key Terms Quick Reference](#13-key-terms-quick-reference)

---

## 1. IAM Fundamentals

### Core IAM Concepts

Identity and Access Management (IAM) is the discipline of ensuring that the **right people** have **the right access** to **the right resources** at **the right time** — and that all of this is **verifiable and auditable**.

IAM addresses three fundamental questions:
- **Authentication (AuthN):** Who are you? — proving identity
- **Authorization (AuthZ):** What are you allowed to do? — granting permissions
- **Accounting/Auditing:** What did you do? — recording activity

### The AAA Framework

```
Authentication ─── Verify identity (prove you are who you claim)
Authorization  ─── Grant permissions (what you can do/access)
Accounting     ─── Record activity (audit trail of what was done)
```

**AAA servers:** Dedicated systems that implement all three AAA functions (RADIUS, TACACS+ are AAA protocols)

### Identification vs. Authentication

**Identification:** Claiming an identity (providing a username, presenting a badge)
- Identification alone provides no assurance — anyone can claim any identity
- Identification must be followed by authentication

**Authentication:** Proving the claimed identity is correct
- Provides assurance that the person is who they claim to be
- Authentication quality depends on the factors used

**Authorization:** Determining what an authenticated identity is permitted to do
- Based on policies, roles, attributes, or rules
- Authorization decisions are enforced by access control mechanisms

### Subjects and Objects

**Subject:** Active entity requesting access to a resource (user, process, application)

**Object:** Passive entity being accessed (file, database record, network resource, system)

**Access control:** The mechanism that mediates between subjects and objects based on policy

```
Subject (user) ──[access request]──► Reference Monitor ──► Object (file)
                                           │
                                     Access Control
                                       Decision
                                       (allow/deny)
```

**Reference Monitor:** Abstract concept of the mechanism that enforces access control policy; must be:
- Complete (mediates all access)
- Isolated (tamper-resistant)
- Verifiable (provably correct)

---

## 2. Authentication Factors

### The Five Authentication Factors

Authentication factors are categories of evidence that prove an identity. Modern identity systems combine multiple factors to increase assurance.

#### Factor 1: Something You Know (Knowledge Factor)

**Definition:** A secret that the authenticating party knows and the verifier can check

**Examples:**
- Passwords and passphrases
- PINs (Personal Identification Numbers)
- Security questions and answers
- Cognitive passwords (childhood pet's name, mother's maiden name)
- Pattern unlock (mobile devices)

**Strengths:**
- Easy to implement
- No hardware required
- User-familiar

**Weaknesses:**
- Subject to guessing, brute force, dictionary attacks
- Subject to phishing and social engineering
- Users choose weak, reused passwords
- Can be observed (shoulder surfing, keyloggers)
- Can be captured in database breaches (if poorly stored)

**Best practices for knowledge factors:**
- Minimum length requirements (NIST SP 800-63B: minimum 8 characters for user-chosen; 6 for system-generated)
- NIST guidance discourages complexity rules and periodic rotation without cause
- Check against known-breached password lists (Have I Been Pwned API)
- Store as salted, iterated hashes (bcrypt, Argon2, PBKDF2) — never plaintext or unsalted MD5/SHA-1
- Account lockout after failed attempts (with care to avoid account lockout DoS)

#### Factor 2: Something You Have (Possession Factor)

**Definition:** A physical or digital token that the authenticating party possesses

**Examples:**
- Hardware OTP tokens (RSA SecurID, YubiKey OTP)
- Smart cards (PIV, CAC)
- FIDO2 hardware security keys (YubiKey FIDO2, Google Titan)
- Software tokens (authenticator apps — Google Authenticator, Microsoft Authenticator)
- SMS OTP (one-time password via text message — see weaknesses)
- Email OTP
- Push notifications (Duo, Okta Verify)

**Strengths:**
- Much harder to steal remotely than passwords
- Physical tokens provide strong assurance when combined with another factor
- FIDO2 hardware keys are phishing-resistant

**Weaknesses:**
- Can be physically lost or stolen
- SMS OTP vulnerable to SIM swapping and SS7 attacks (considered RESTRICTED, not recommended for sensitive systems by NIST)
- Software tokens vulnerable if device is compromised
- Push notification "fatigue" — users may approve prompts without verifying

#### Factor 3: Something You Are (Inherence Factor / Biometric)

**Definition:** Biological or behavioral characteristics of the authenticating party

**Physiological biometrics:**
- Fingerprint
- Retina scan
- Iris scan
- Facial recognition
- Hand geometry / vein pattern
- DNA (impractical for authentication — too slow)

**Behavioral biometrics:**
- Keystroke dynamics (typing rhythm and pressure)
- Voice recognition / speaker verification
- Signature dynamics (pen pressure, speed, angle — not the signature itself)
- Gait analysis
- Mouse movement patterns

**Biometric strengths:**
- Cannot be forgotten
- Difficult to share (unlike passwords)
- Some types very difficult to forge

**Biometric weaknesses:**
- Cannot be revoked or reset if compromised (unlike a password)
- Privacy concerns — immutable biological data
- Subject to spoofing (face photos, fake fingerprints, voice recordings)
- False acceptance and false rejection errors — no biometric is perfect
- Sensor quality affects performance
- Legal issues around collection and storage of biometric data (BIPA in Illinois, GDPR Article 9)

#### Factor 4: Somewhere You Are (Location Factor)

**Definition:** Physical or logical location of the authenticating party

**Examples:**
- IP geolocation — is the login originating from an expected country/city/ASN?
- GPS coordinates (mobile device)
- Network location — is the device on the corporate network or a trusted VPN?
- Cell tower triangulation

**Use in authentication:**
- Primarily used as a risk signal in adaptive/risk-based authentication (not typically a standalone factor)
- Login from unexpected country → trigger step-up authentication
- Login from known corporate network → reduce friction

**Limitations:**
- IP geolocation can be spoofed via VPNs and proxies
- Attacker on compromised internal network would appear to be at correct location
- Privacy concerns with precise location tracking

#### Factor 5: Something You Do (Behavior Factor)

**Definition:** Behavioral patterns that are characteristic of the individual

**Examples:**
- Keystroke dynamics (covered under biometric behavioral above)
- Continuous authentication based on behavioral baseline
- Transaction behavior analysis (unusual purchase patterns trigger step-up auth)

**Use:** Primarily in continuous authentication and fraud detection systems; less common as a primary authentication factor

### Factor Combination Rules

**Multi-factor authentication (MFA):** Using two or more factors from different categories

**IMPORTANT for CISSP exam:** Factors must be from **different categories**:

| Combination | MFA? | Reason |
|-------------|------|--------|
| Password + PIN | NO | Both are "something you know" |
| Password + OTP token | YES | "know" + "have" |
| Fingerprint + face scan | NO | Both are "something you are" |
| Smart card + PIN | YES | "have" + "know" |
| Password + push notification + fingerprint | YES | "know" + "have" + "are" |

---

## 3. Authentication Protocols

### Kerberos

**Overview:** Network authentication protocol developed at MIT; used extensively in Microsoft Active Directory environments. Provides SSO within a realm using a trusted third-party ticket system. Does not use passwords over the network.

**Key components:**

| Component | Description |
|-----------|------------|
| **KDC (Key Distribution Center)** | Trusted server that issues tickets; contains AS and TGS |
| **AS (Authentication Service)** | Authenticates the user; issues TGT |
| **TGS (Ticket Granting Service)** | Issues service tickets when presented with valid TGT |
| **TGT (Ticket Granting Ticket)** | Proof of authentication; used to request service tickets; time-limited |
| **Service Ticket (ST)** | Grants access to a specific service; presented to the target service |
| **Realm** | Administrative domain; users, services, and KDC in same realm trust each other |
| **Principal** | Any entity with a Kerberos identity (user or service) |

**Kerberos Authentication Flow:**

```
Step 1: Client → AS: "I am Alice" (plaintext; includes timestamp)
Step 2: AS → Client:
    - TGT (encrypted with KDC's secret key — client cannot read this)
    - Session key (encrypted with Alice's derived key/password hash)
    [Client decrypts session key using password; stores TGT for later use]

Step 3: Client → TGS: "I want to access File Server" + TGT + Authenticator
    [Authenticator = timestamp encrypted with session key — proves freshness]
Step 4: TGS → Client:
    - Service Ticket (encrypted with file server's secret key)
    - Service session key (encrypted with session key)

Step 5: Client → File Server: Service Ticket + new Authenticator
Step 6: File Server → Client: Confirmation (mutual authentication)
    [File server decrypts service ticket with its secret key; verifies authenticator]
```

**Key Kerberos security properties:**
- Passwords never transmitted over the network
- Tickets are time-limited (typically 8-10 hours for TGT; prevent replay)
- Timestamps prevent replay attacks (clock skew tolerance typically ±5 minutes)
- Mutual authentication possible (client and server authenticate to each other)

**Kerberos attacks:**
- **Pass-the-Hash (PtH):** Attacker captures password hash and uses it directly without knowing plaintext password
- **Pass-the-Ticket (PtT):** Attacker steals a valid TGT or service ticket from memory (e.g., via Mimikatz)
- **Kerberoasting:** Attacker requests service tickets for service accounts; offline brute-force of the ticket encryption (uses service account's password hash)
- **Golden Ticket:** Attacker with krbtgt hash can forge TGTs for any user, including non-existent users; persists even after password changes
- **Silver Ticket:** Forged service ticket using compromised service account hash; more limited than Golden Ticket
- **AS-REP Roasting:** Attacks accounts with Kerberos pre-authentication disabled; captures AS response for offline cracking

### SAML 2.0 — Security Assertion Markup Language

**Overview:** XML-based open standard for exchanging authentication and authorization data between parties (Identity Provider and Service Provider). Primary use: enterprise SSO and federated identity.

**Roles:**
- **Identity Provider (IdP):** Authenticates the user; asserts identity to SP (e.g., Okta, Azure AD, ADFS)
- **Service Provider (SP):** Relies on IdP's assertion to grant access (e.g., Salesforce, Google Workspace, AWS console)
- **Principal (User/Subject):** The entity whose identity is being asserted

**Three types of SAML assertions:**
1. **Authentication assertion:** Confirms the principal was authenticated by the IdP, how, and when
2. **Attribute assertion:** Conveys attributes about the principal (email, group membership, role, department)
3. **Authorization decision assertion:** States whether the principal is permitted to access a specific resource

**SAML 2.0 SP-Initiated SSO Flow (most common):**

```
1. User → SP: Requests protected resource (https://app.company.com/dashboard)
2. SP: Generates SAML AuthnRequest; redirects user to IdP
3. User → IdP: Browser follows redirect to IdP (https://idp.company.com/sso)
4. IdP: Authenticates user (username/password + MFA)
5. IdP → User (browser): Returns SAML Response (assertion) in HTML form POST
6. User (browser) → SP: Browser auto-submits form with SAML Response
7. SP: Validates assertion signature; checks conditions (NotBefore, NotOnOrAfter)
8. SP → User: Grants access to requested resource
```

**SAML assertion structure (simplified):**

```xml
<samlp:Response>
  <saml:Issuer>https://idp.company.com</saml:Issuer>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion>
    <saml:Issuer>https://idp.company.com</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
        alice@company.com
      </saml:NameID>
    </saml:Subject>
    <saml:Conditions NotBefore="2026-03-01T10:00:00Z"
                     NotOnOrAfter="2026-03-01T10:05:00Z"/>
    <saml:AuthnStatement AuthnInstant="2026-03-01T10:00:00Z">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>
          urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
        </saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>
    <saml:AttributeStatement>
      <saml:Attribute Name="role">
        <saml:AttributeValue>analyst</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>
```

**SAML security considerations:**
- Assertions must be digitally signed by the IdP to prevent forgery
- SP must validate the signature before trusting the assertion
- Time conditions (NotBefore/NotOnOrAfter) prevent replay attacks
- Assertion consumers must match registered ACS URLs to prevent open redirect
- XML Signature Wrapping (XSW) attacks: attacker manipulates XML structure while preserving signature validity — implementations must validate signing scope

### OAuth 2.0

**Overview:** Authorization framework (NOT an authentication protocol) that allows a user to grant a third-party application limited access to their resources on a service, without sharing credentials.

**Key distinction:** OAuth 2.0 provides **authorization** (access to resources). It was not designed for authentication. Using OAuth 2.0 alone for authentication is a security antipattern — use OpenID Connect instead.

**OAuth 2.0 roles:**
- **Resource Owner:** User who owns the protected resource; grants authorization
- **Client:** Application requesting access (web app, mobile app, CLI)
- **Authorization Server (AS):** Issues access tokens after authenticating resource owner and obtaining consent
- **Resource Server (RS):** Hosts the protected resources; validates access tokens

**OAuth 2.0 grant types:**

| Grant Type | Use Case | Flow |
|-----------|---------|------|
| **Authorization Code** | Server-side web apps (most secure) | Code exchanged server-side for tokens; PKCE extends for SPAs/mobile |
| **Authorization Code + PKCE** | SPAs and mobile apps | Proof Key for Code Exchange prevents code interception |
| **Client Credentials** | Machine-to-machine (no user) | Direct token request using client ID + secret |
| **Device Code** | Devices without browsers (TV, IoT) | Device displays code; user authenticates on separate device |
| **Implicit** | DEPRECATED — insecure; tokens in URL fragment | N/A — replaced by Auth Code + PKCE |

**Authorization Code Flow:**

```
1. User → Client: "Login with Google"
2. Client → Authorization Server: Redirect with:
   - response_type=code
   - client_id
   - redirect_uri
   - scope (e.g., "read:email calendar:read")
   - state (CSRF protection)
   - code_challenge (PKCE — hash of code_verifier)

3. AS → User: Authentication + Consent screen
4. User → AS: Grants consent
5. AS → Client (redirect): Authorization code + state

6. Client → AS: Exchange code for tokens:
   - grant_type=authorization_code
   - code
   - code_verifier (PKCE)
   - client_secret (server-side apps)

7. AS → Client: Access token (JWT) + Refresh token

8. Client → Resource Server: API request with Bearer token
9. RS: Validates token → returns protected resource
```

**OAuth 2.0 token types:**
- **Access token:** Short-lived credential granting access to specific resources/scopes (minutes to hours)
- **Refresh token:** Longer-lived credential used to obtain new access tokens without re-authentication (days to weeks; stored securely)
- **JWT (JSON Web Token):** Common access token format; self-contained (carries claims); signed by AS; RS validates signature without calling AS

**JWT structure:**

```
Header.Payload.Signature

Header: {"alg": "RS256", "typ": "JWT"}
Payload: {
  "sub": "alice@company.com",
  "iss": "https://auth.company.com",
  "aud": "https://api.company.com",
  "exp": 1772525400,
  "iat": 1772521800,
  "scope": "read:data"
}
Signature: RS256(base64url(header) + "." + base64url(payload), private_key)
```

### OpenID Connect (OIDC)

**Overview:** Authentication layer built on top of OAuth 2.0. Where OAuth 2.0 answers "what can the application access?", OIDC answers "who is the user?". Adds an **ID token** containing user identity claims.

**OIDC additions to OAuth 2.0:**
- **ID Token:** JWT containing user identity information (not authorization)
- **UserInfo Endpoint:** Resource server endpoint that returns additional user claims
- **Standard claims:** sub, name, email, email_verified, phone_number, profile, picture
- **Authentication Context Reference (ACR):** Indicates how the user was authenticated (password-only vs. MFA)

**ID Token claims:**

```json
{
  "iss": "https://idp.company.com",
  "sub": "alice-unique-identifier-12345",
  "aud": "client-app-id",
  "exp": 1772525400,
  "iat": 1772521800,
  "auth_time": 1772521800,
  "nonce": "abc123",
  "acr": "urn:mace:incommon:iap:silver",
  "amr": ["pwd", "otp"],
  "name": "Alice Chen",
  "email": "alice@company.com",
  "email_verified": true
}
```

**OIDC vs. SAML comparison:**

| Feature | SAML 2.0 | OIDC |
|---------|----------|------|
| Format | XML | JSON / JWT |
| Transport | Browser form POST | HTTPS redirect + API |
| Age | 2005 | 2014 |
| Mobile-friendly | Poor | Excellent |
| Enterprise adoption | High | Growing rapidly |
| Assertion signing | XML Signature | JWS (RS256, ES256) |
| Use cases | Enterprise SSO | Web, mobile, APIs |

### FIDO2 / WebAuthn

**Overview:** W3C and FIDO Alliance standards for phishing-resistant, passwordless authentication. Uses public-key cryptography. Two components: **WebAuthn** (browser API) and **CTAP2** (protocol between authenticator and browser/platform).

**Key security properties:**
- **Origin-bound:** Credentials are bound to the specific domain (origin); cannot be used on phishing sites
- **No shared secrets:** Server stores only a public key; private key never leaves the authenticator
- **Phishing-resistant:** Cryptographic challenge-response; not susceptible to credential phishing
- **Attestation:** Hardware authenticators can prove their security properties to the server

**FIDO2 authenticator types:**

| Type | Examples | Notes |
|------|---------|-------|
| **Platform authenticator** | Windows Hello (face/fingerprint), Apple Touch ID / Face ID | Built into device; uses device's secure enclave |
| **Roaming authenticator** | YubiKey, Google Titan, SoloKey | External hardware key; connects via USB, NFC, BLE |
| **Hybrid (passkey)** | Phone-as-authenticator via Bluetooth | Cross-device authentication using nearby phone |

**FIDO2 Registration Flow:**

```
1. User initiates registration on website
2. Server → Browser: Challenge (random bytes), rpId, pubKeyCredParams
3. Browser → Authenticator: Create credential request
4. Authenticator:
   - Generates public/private key pair bound to rpId (domain)
   - Stores private key securely (TPM, secure enclave, hardware security element)
   - Returns public key + attestation to browser
5. Browser → Server: Public key + credential ID + attestation
6. Server: Stores public key + credential ID for user account
```

**FIDO2 Authentication Flow:**

```
1. User presents authenticator (touches key, scans fingerprint, etc.)
2. Server → Browser: Challenge (fresh random bytes), rpId, allowCredentials
3. Browser → Authenticator: Sign challenge
4. Authenticator:
   - Verifies user presence (touch) and user verification (PIN/biometric) if required
   - Signs challenge with private key
   - Returns signature + authenticator data (counter, flags)
5. Browser → Server: Signature + authenticator data
6. Server:
   - Verifies signature using stored public key
   - Checks rpId matches server's domain
   - Verifies counter (detects cloned authenticators if counter doesn't increment)
   - Grants access
```

**Passkeys:** Discoverable FIDO2 credentials synchronized across devices via cloud keychain (iCloud Keychain, Google Password Manager). More convenient than hardware keys; still phishing-resistant; appropriate for most consumer and enterprise scenarios.

---

## 4. Access Control Models

### Discretionary Access Control (DAC)

**Definition:** Access control based on the identity of subjects and object ownership. The **owner** of the object decides who can access it and what they can do.

**Key characteristics:**
- Object owner (typically the creator) controls the ACL (Access Control List)
- Owners can grant/revoke access to others
- Owners can delegate grant authority to others (transitive — a security weakness)
- Highly flexible; user-driven

**Implementation:**
- File system ACLs (Unix permissions: rwxr-xr-x, Windows DACL)
- Share permissions
- Database object ownership

**Strengths:**
- Flexible; users can control their own data
- Familiar model to end users
- Good for collaborative environments

**Weaknesses:**
- Difficult to enforce organization-wide policy (users may misconfigure permissions)
- Permissions can propagate uncontrollably (Trojan horse problem)
- No protection against malicious owners
- Not suitable for high-security environments

**Example:**
Alice creates a document and sets the ACL to allow Bob read access. Alice can also grant Bob write access or grant Carol access. The organization cannot prevent Alice from granting inappropriate access (within DAC).

### Mandatory Access Control (MAC)

**Definition:** Access control enforced by the system based on labels (classifications) and clearances; the **system** makes access decisions based on policy — neither users nor owners can override.

**Key characteristics:**
- Security labels on objects (sensitivity level: Top Secret, Secret, Confidential, Unclassified)
- Clearances assigned to subjects
- The security kernel enforces policy; no exceptions
- Users cannot grant access to others beyond their own level

**Bell-LaPadula Model (Confidentiality MAC):**

```
Rule 1: No Read Up (Simple Security Property)
  → Subject cannot read object at a higher classification than subject's clearance
  → Prevents unauthorized disclosure

Rule 2: No Write Down (*-Property / Star Property)
  → Subject cannot write to an object at a lower classification
  → Prevents data leakage from high to low classification

Rule 3: Discretionary Security Property
  → Use access matrix to further restrict read/write
```

**Biba Model (Integrity MAC):**

```
Rule 1: No Write Up (Simple Integrity Property)
  → Subject cannot write to an object at a higher integrity level
  → Prevents corruption of trusted data by untrusted subjects

Rule 2: No Read Down (*-Integrity Property)
  → Subject cannot read from lower integrity level objects
  → Prevents contamination of high-integrity processing with untrusted data
```

**MAC implementations:**
- Military/government classified systems (NSA, DoD)
- SELinux (Security-Enhanced Linux) — implements Type Enforcement (TE) + RBAC + MLS
- AppArmor (path-based MAC for Linux)
- TrustedBSD / FreeBSD MAC framework

**Strengths:**
- Strongest protection against unauthorized disclosure
- Cannot be overridden by users or owners
- Suitable for high-security environments (classified systems, financial systems)

**Weaknesses:**
- Inflexible; difficult to administer
- Performance overhead
- Complex label management
- Can impede normal business operations

### Role-Based Access Control (RBAC)

**Definition:** Permissions are assigned to roles, and roles are assigned to users. Users gain permissions through their role memberships, not through individual grants.

**Key characteristics:**
- Roles represent job functions (administrator, analyst, auditor, read-only)
- Permissions are tied to roles, not individual users
- Users are assigned to roles based on job function
- Separation of duties enforced through role separation

**RBAC components (NIST RBAC model):**
- **RBAC₀ (Core RBAC):** Users, roles, permissions, sessions; user-role and role-permission assignments
- **RBAC₁ (Hierarchical RBAC):** Role hierarchy; senior roles inherit permissions of junior roles
- **RBAC₂ (Constrained RBAC):** Static and dynamic separation of duty constraints
- **RBAC₃ (Symmetric RBAC):** Combines hierarchy and constraints

**Example role hierarchy:**

```
Admin
  └── Manager
       └── Analyst
            └── Read-Only

Admin inherits all permissions of Manager, Analyst, and Read-Only
```

**Separation of duty in RBAC:**
- **Static SoD (SSD):** User cannot hold both roles simultaneously (e.g., cannot be both accounts payable and accounts receivable)
- **Dynamic SoD (DSD):** User may hold both roles but cannot activate both in the same session

**Strengths:**
- Matches how organizations actually think about access (job functions)
- Easy to administer at scale
- Audit-friendly: who has what roles is easy to review
- Enforcement of separation of duties

**Weaknesses:**
- Role explosion: too many granular roles become unmanageable
- Does not natively handle context (time, location, risk level)
- Access based on role, not actual need for a specific object

### Attribute-Based Access Control (ABAC)

**Definition:** Access decisions based on attributes of the subject, object, action, and environment. Policy language combines multiple attributes using Boolean logic.

**Key characteristics:**
- Fine-grained policy expressions
- Attributes can represent anything: subject department, object classification, time, location, device risk score
- Policy Decision Point (PDP) evaluates policy against attributes; Policy Enforcement Point (PEP) enforces the decision
- XACML (eXtensible Access Control Markup Language) is the standard policy language

**ABAC architecture:**

```
Subject ──[request]──► PEP (Policy Enforcement Point)
                           │
                           ▼
                        PAP (Policy Administration Point)
                           │ policies
                           ▼
                        PDP (Policy Decision Point)
                           │
                        PIP (Policy Information Point)
                           │ attributes
```

**Example ABAC policy:**

```
PERMIT access IF:
  subject.clearance >= object.classification
  AND subject.department == object.owning_department
  AND action IN ["read", "download"]
  AND environment.time BETWEEN "08:00" AND "20:00"
  AND environment.network IN ["corporate", "vpn"]
  AND subject.mfa_verified == true
```

**Strengths:**
- Extremely fine-grained
- Context-aware (time, location, device state)
- Policy can incorporate risk signals
- Scales well to complex environments

**Weaknesses:**
- Complex to design and maintain
- Policy debugging can be difficult
- Performance overhead for complex policy evaluation
- Requires robust attribute pipeline (attributes must be authoritative and fresh)

### Rule-Based Access Control

**Definition:** Access decisions based on rules — typically system-defined conditions that are not tied to individual users or roles.

**Key characteristics:**
- Rules apply globally to all users attempting to perform an action
- Common in network security devices
- Rules evaluate conditions: time, location, source/destination IP, protocol, port

**Examples:**
- Firewall ACL: "DENY any traffic from 10.0.0.0/8 to DMZ on port 22"
- Router ACL: "PERMIT TCP from 192.168.1.0/24 to any port 443"
- Time-based access: "DENY all user logins between 02:00 and 04:00"

**Note:** Rule-based is sometimes confused with RBAC. Key difference: Rule-based rules are system-defined and apply universally; RBAC is about user-role assignments.

### Access Control Model Comparison

| Model | Decision Basis | Who Controls | Best For | Example |
|-------|---------------|-------------|---------|---------|
| DAC | Object ownership | Object owner | Collaborative environments | Windows NTFS, shared drives |
| MAC | Labels/clearances | System/kernel | High-security (classified) | NSA systems, SELinux |
| RBAC | Role membership | Administrator | Enterprise access management | Active Directory groups |
| ABAC | Multi-attribute policy | Policy administrators | Fine-grained, context-aware | AWS IAM policies, XACML |
| Rule-based | System rules | System/network admin | Network devices, time controls | Firewalls, routers |

---

## 5. Identity Federation and SSO

### Federation Overview

Identity federation is the process of linking identities across different administrative domains (organizations, cloud services, applications) so that a user authenticated in one domain can access resources in another without re-authenticating.

**Trust relationships:** Federation requires establishing trust between domains. The IdP (Identity Provider) and SP (Service Provider) must:
- Agree on the identity protocol (SAML, OIDC, WS-Federation)
- Exchange metadata (endpoints, certificates, supported bindings)
- Establish contract terms around liability, data handling, and SLAs

### Single Sign-On (SSO)

**Definition:** Authentication mechanism where a user logs in once and gains access to multiple applications without re-authenticating for each one.

**Benefits:**
- Improved user experience (one password/login to manage)
- Reduced password fatigue (fewer passwords → stronger passwords)
- Centralized authentication → easier MFA enforcement
- Centralized audit trail
- Single point of deprovisioning

**SSO types:**

| Type | Description | Protocol |
|------|------------|---------|
| **Enterprise SSO** | Within organization; internal apps | Kerberos, SAML |
| **Web SSO** | Across web applications | SAML, OIDC |
| **Federated SSO** | Across organizational boundaries | SAML, OIDC, WS-Federation |

**SSO risk:** If the SSO credential is compromised, all integrated applications are compromised — "blast radius" is large. This makes MFA at the SSO layer critical.

### SAML Federation in Detail

**SAML metadata:** XML document exchanged between IdP and SP; contains:
- Entity ID (unique identifier for the entity)
- Certificate(s) for signature verification and encryption
- Supported bindings (HTTP Redirect, HTTP POST, Artifact)
- Endpoint URLs (SSO URL, ACS URL, SLO URL)

**SAML bindings:**
- **HTTP Redirect binding:** SAML message encoded in URL query string (limited to ~8KB); used for AuthnRequest
- **HTTP POST binding:** SAML message in HTML form body; used for larger assertions
- **Artifact binding:** A reference (artifact) is passed via URL; SP fetches full assertion from IdP using artifact via SOAP call

**Single Logout (SLO):** SAML supports federated logout; when user logs out of SP, SP sends LogoutRequest to IdP, which propagates logout to all other SPs in the session.

### Trust Models in Federation

**Direct trust:** IdP and SP have a direct bilateral relationship; each has the other's certificate and metadata. Common in small-scale deployments.

**Brokered trust (hub-and-spoke):** A central identity broker (e.g., Okta, Azure AD, Ping Identity) establishes trust with many IdPs and SPs. Organizations connect to the broker rather than establishing bilateral relationships with every partner.

**Web of trust:** Decentralized; entities trust others based on vouching. Less common in enterprise IAM.

**Federation consortiums:** Groups of organizations agree on standards and operate a shared trust fabric (e.g., InCommon for US higher education, edugain for international academic federation).

### Cross-Domain Trust

**Active Directory Trusts:**
- **One-way trust:** Domain A trusts Domain B; users in B can access resources in A (not vice versa)
- **Two-way trust:** Bidirectional; users in either domain can access resources in both
- **Transitive trust:** If A trusts B and B trusts C, A trusts C
- **Non-transitive trust:** Trust does not pass through; each relationship must be explicit
- **External trust:** Between AD DS domains in different forests; non-transitive by default
- **Forest trust:** Between AD forests; can be transitive; requires explicit setup

---

## 6. Privileged Access Management (PAM)

### What Is Privileged Access?

Privileged access refers to accounts, credentials, and systems with elevated permissions beyond those of standard users. Privileged accounts can:
- Modify security configurations
- Access sensitive data without restrictions
- Create or modify other accounts
- Install software or modify system configurations
- Disable audit logging

**Types of privileged accounts:**

| Account Type | Examples | Risk |
|-------------|---------|------|
| Local admin | Built-in Administrator on Windows, root on Linux | Shared passwords often unchanged for years |
| Domain admin | AD Domain Admins, Enterprise Admins | Control entire AD forest |
| Service accounts | Application accounts, scheduled task accounts | Often have excessive privileges; infrequently reviewed |
| Emergency/break-glass | "firecall" accounts for emergencies | Must be audited carefully; rarely used |
| Shared accounts | Generic "admin" accounts | No individual accountability |
| Cloud admin | AWS root account, Azure Global Administrator | Can modify all cloud resources and IAM |
| Application API keys | Service-to-service authentication | Often embedded in code; difficult to rotate |

### PAM Architecture

**PAM solution components:**
- **Credential vault:** Encrypted storage for privileged credentials; serves as the authoritative source
- **Session manager/proxy:** Intercepts and manages privileged sessions; records all activity
- **Password manager:** Automates credential rotation on schedule or after use
- **Discovery:** Scans environment to find unmanaged privileged accounts and credentials
- **Policy engine:** Defines who can request what privilege, when, with what approval workflow
- **Reporting/analytics:** Audit trails, anomaly detection, compliance reporting

### PASM — Privileged Account and Session Management

**Definition:** Traditional PAM paradigm. Privileged accounts exist in the vault; users check out credentials, establish sessions through the proxy, and credentials are rotated after use.

**PASM capabilities:**
- Credential vaulting and rotation
- Session recording (keystrokes, screen capture, command logging)
- Session brokering (proxy architecture — user never sees credentials directly)
- Access request workflow (require manager approval, ticket number, justification)
- Automated credential rotation (after each use, on schedule)
- Real-time session monitoring and termination
- Integration with SIEM and ticketing systems

**PASM workflow:**

```
1. User requests access to target system
2. PAM policy engine: Is user authorized? Is there a valid change ticket?
3. Approval workflow (automated or human approval)
4. PAM vault issues temporary session credentials (user may not see the actual password)
5. Session established through PAM proxy (all activity recorded)
6. User completes work; session closed
7. PAM rotates credential on target system
8. Session recording archived for audit
```

### PEDM — Privilege Elevation and Delegation Management

**Definition:** Controls what privileged commands or operations a user can execute on a system they already have access to, without granting full administrative access.

**PEDM on endpoints:**
- Application whitelisting with elevated privilege for specific apps (user can install approved apps without being a local admin)
- Sudo policy management (Linux/macOS: what commands can specific users run as root)
- Windows UAC enhancement: specific applications can run elevated without admin credentials
- Just-enough-access: grant minimum necessary privilege for a specific task

**PEDM vs. PASM:**

| | PASM | PEDM |
|--|------|------|
| **Focus** | Managing who can access privileged accounts | Managing what privileged commands users can execute |
| **Mechanism** | Credential vault + session proxy | Privilege broker on endpoint/server |
| **Typical use** | Server administration, database access | Endpoint admin tasks, specific elevated commands |

### Just-in-Time (JIT) Access

**Definition:** Privileged access is granted dynamically for a specific duration and purpose, then automatically revoked. The privileged account may be created on-demand and destroyed afterward.

**JIT models:**

**Just-in-Time account creation:**
- Privileged account created at time of request
- Time-limited (e.g., 2-hour window)
- Automatically deleted/disabled after session ends
- No persistent privileged account exists — nothing to steal or exploit between uses

**Just-in-Time privilege elevation:**
- Standard user account receives temporary elevated permissions
- Elevation tied to specific approved request/ticket
- Automatically expires

**Benefits of JIT:**
- Eliminates persistent privileged accounts (standing privilege)
- Dramatically reduces attack surface
- Every use requires a justification and approval
- Full audit trail for all elevated activity
- Aligns with zero trust principle: never trust, always verify

**JIT in cloud environments:**
- AWS: IAM role assumption with temporary credentials (STS AssumeRole with time-limited sessions)
- Azure: Azure AD Privileged Identity Management (PIM) — eligible vs. active roles
- GCP: Workforce Identity Federation with time-limited role grants

### Least Privilege Principle

**Definition:** Users, processes, and systems should have only the minimum permissions necessary to perform their assigned functions — nothing more.

**Application of least privilege:**
- **User accounts:** No local admin rights by default; admin access only for administrative tasks
- **Service accounts:** Only the specific permissions the service needs; not Domain Admin unless absolutely required
- **API keys/tokens:** Scoped to specific resources and actions
- **Applications:** Run with minimal OS permissions; no unnecessary services enabled
- **Network:** Firewall rules allow only necessary traffic; default deny
- **Database accounts:** Application DB users have only SELECT/INSERT/UPDATE on required tables; not DBA

**Least privilege audit:** Periodically review assigned permissions against actual usage (access analytics); remove unused permissions.

---

## 7. Account Lifecycle Management

### Account Provisioning

**Definition:** The process of creating an account, assigning appropriate permissions, and enabling access for a new user or service.

**Provisioning workflow:**
1. HR notifies IT of new hire (position, start date, department, manager)
2. Joiner workflow triggered: create accounts in all required systems
3. Role assignment based on job function (RBAC)
4. Access approved by manager or HR
5. Credentials delivered securely (not plaintext email)
6. Access confirmation by user on first login

**Provisioning automation:**
- **SCIM (System for Cross-domain Identity Management):** REST-based protocol for automating user provisioning across applications; IdP pushes user lifecycle events to apps
- **HR-driven provisioning:** HRIS as authoritative source; changes in HRIS trigger automatic account changes
- **Identity governance platforms:** SailPoint, Saviynt, One Identity — orchestrate provisioning across complex environments

**Access request process (for non-automatic access):**
1. User or manager submits access request (ServiceNow, Jira, IAM portal)
2. Request routed for approval (data owner, manager, security team)
3. Provisioned upon approval; request and justification logged
4. Periodic recertification of granted access

### Access Recertification (Access Review / Certification)

**Definition:** Periodic review of user access rights to confirm that assigned permissions are still appropriate and necessary.

**Why recertification matters:**
- Access accumulates over time ("access creep") as users change roles
- Roles may become inappropriate after job changes
- Orphaned accounts (ex-employees) may persist if offboarding is manual
- Regulatory requirements often mandate periodic review (SOX, HIPAA, PCI DSS)

**Recertification types:**
- **User access review:** Manager certifies each direct report's access is appropriate
- **Role review:** Role owner certifies that role permissions are still appropriate
- **Entitlement review:** Data owner certifies who should have access to their data
- **Privileged access review:** More frequent review of privileged account assignments

**Recertification frequency best practices:**

| Account Type | Recommended Frequency |
|-------------|----------------------|
| Standard user accounts | Annual |
| Privileged accounts | Quarterly or more frequent |
| Service accounts | Semi-annual |
| Third-party/vendor accounts | Before each engagement period |
| Terminated employees | Immediate |

### Deprovisioning

**Definition:** Removing access rights when they are no longer needed (employee termination, role change, project completion, vendor relationship ending).

**Offboarding checklist:**

| Action | Timing |
|--------|--------|
| Disable primary account (AD, IdP) | On last day / at notification |
| Revoke VPN and remote access | Immediately |
| Disable email | Last day (after forwarding set up if needed) |
| Recover equipment (laptop, tokens, badges) | Last day |
| Transfer owned files/data | Before access revoked |
| Rotate shared credentials known to the user | Immediately |
| Archive account and data per retention policy | Within 30 days |
| Remove from distribution lists | Within 30 days |
| Delete account | Per retention policy (often 90 days for recovery window) |

**Access creep:** Users accumulate permissions over time as they change roles. Each new role adds permissions; old permissions are rarely removed. Recertification campaigns and automatic deprovisioning are controls for this problem.

**Orphaned accounts:** Accounts that remain active after the associated user has left the organization. Pose significant insider threat and account takeover risk. Regular account audits comparing active accounts against HR records detect orphaned accounts.

---

## 8. Zero Trust Principles

### Zero Trust Architecture Overview

**Definition:** A security model that assumes no user, device, or network is inherently trustworthy — even if inside the traditional network perimeter. Every access request must be explicitly authenticated, authorized, and continuously validated.

**Origin:** Coined by John Kindervag at Forrester Research (2010); "never trust, always verify"

**Core tenets (NIST SP 800-207):**

1. All data sources and computing services are considered resources
2. All communication is secured regardless of network location
3. Access to individual enterprise resources is granted on a per-session basis
4. Access to resources is determined by dynamic policy (including identity, application/service, device state, and other behavioral and environmental attributes)
5. The enterprise monitors and measures the integrity and security posture of all owned and associated assets
6. All resource authentication and authorization is dynamic and strictly enforced before access is allowed
7. The enterprise collects as much information as possible about the current state of assets, network infrastructure, and communications and uses it to improve its security posture

### Zero Trust vs. Traditional Perimeter Security

| Traditional | Zero Trust |
|------------|-----------|
| "Castle and moat" — trust everything inside | Verify everything, trust nothing implicitly |
| VPN grants broad network access | Identity and context determine per-resource access |
| North-south focused (in/out) | East-west traffic also inspected |
| Device trust based on network location | Device trust based on health/compliance state |
| Static, coarse-grained authorization | Dynamic, fine-grained, continuous authorization |
| Annual access reviews | Continuous access evaluation |

### Zero Trust Pillars

Modern Zero Trust frameworks (CISA ZTA, DoD ZTA) organize capabilities into pillars:

```
IDENTITY  ─── Strong authentication, MFA, identity governance
DEVICE    ─── Device health/compliance checks, EDR, MDM enrollment
NETWORK   ─── Microsegmentation, ZTNA, encrypted communications
APPLICATION─── Application-layer controls, WAF, API gateway
DATA      ─── Data classification, DLP, encryption, access analytics
```

### Zero Trust Network Access (ZTNA)

**Definition:** Replaces VPN with application-specific access that is policy-controlled, identity-aware, and does not grant network-level access.

**How ZTNA works:**
1. User authenticates to ZTNA broker/controller
2. Device health is assessed (patch level, EDR status, OS version)
3. Identity + device context evaluated against policy
4. If policy allows: user gains access to **specific application**, not the whole network
5. Traffic flows through encrypted tunnel to app; network not exposed to user

**ZTNA vs. VPN:**

| VPN | ZTNA |
|-----|------|
| Network-level access (user on segment can reach any device) | Application-level access only |
| No ongoing device validation | Continuous device health assessment |
| User traffic traverses corporate network | Direct-to-cloud or broker-mediated |
| Coarse-grained control | Fine-grained policy per application |
| Lateral movement possible after compromise | Lateral movement significantly restricted |

### Continuous Adaptive Risk and Trust Assessment (CARTA)

Gartner's model for continuous evaluation of risk and trust during a session — not just at authentication time:

```
At request time → Authenticate and authorize
During session → Monitor for anomalies (unusual data downloads, off-hours access, new device)
Dynamically → Increase authentication requirements if risk rises
Automatically → Terminate session or require step-up auth if anomaly detected
```

---

## 9. MFA Types and Resistance Levels

### Phishing-Resistant vs. Phishable MFA

Not all MFA is equally secure. CISA and NIST guidance distinguishes between phishing-resistant and phishable authenticators.

**Phishable MFA (susceptible to AiTM — Adversary in the Middle — attacks):**

| Type | Attack Vector | Risk Level |
|------|-------------|-----------|
| SMS OTP | SIM swap, SS7 interception, real-time phishing relay | High |
| Email OTP | Account takeover, real-time phishing relay | High |
| TOTP (authenticator apps) | Real-time phishing relay (attacker forwards code) | Medium-High |
| Push notification | Fatigue attacks (MFA bombing), real-time relay | Medium |

**How AiTM phishing bypasses TOTP/push:**
1. User navigates to realistic phishing site
2. Phishing site acts as proxy between user and real site
3. User enters credentials and MFA code on phishing site
4. Phishing site relays credentials and MFA code to real site in real time
5. Attacker obtains valid authenticated session cookie
6. User sees "error" or is redirected; attacker has full access

**Phishing-resistant MFA:**

| Type | Mechanism | Resistance |
|------|-----------|-----------|
| FIDO2 hardware key | Public key crypto; credential bound to origin (domain) | Highest |
| Passkeys (FIDO2) | Platform authenticator with cloud sync | High |
| PIV/CAC smart card | Certificate-based; PKI | High |
| Windows Hello for Business | Platform authenticator; certificate-backed | High |

**Why FIDO2 is phishing-resistant:** The credential is cryptographically bound to the specific domain (origin). When authenticating, the browser includes the RP ID (domain) in the challenge. If the user is on a phishing domain, the browser will not release the credential for that domain — even if the domain looks identical. There is no secret to steal and relay.

### NIST SP 800-63B Authentication Assurance Levels (AAL)

NIST defines three Authentication Assurance Levels (AAL) that map to authentication strength:

| AAL | Description | Allowed Authenticators |
|-----|------------|----------------------|
| **AAL1** | Basic assurance; single factor OK | Password, OTP, TOTP |
| **AAL2** | Moderate assurance; MFA required | MFA with password + possession factor; requires proof of possession |
| **AAL3** | High assurance; hardware required; verifier impersonation resistance required | FIDO2 hardware key, PIV/CAC; requires physical presence verification |

**When AAL3 is required:** High-impact transactions, access to highly sensitive data, privileged administrative functions in high-security environments.

### Push Notification Security

**MFA fatigue / push bombing:**
- Attacker has compromised credentials (from breach database)
- Attacker initiates multiple login attempts
- User receives repeated push notifications
- Fatigued user taps "Approve" to stop the notifications
- Attacker gains access

**Mitigations for push fatigue:**
- **Number matching:** Push notification shows a number; user must enter matching number from login screen (prevents blind approval)
- **Geolocation display:** Push shows location of login attempt; user can reject suspicious locations
- **Context-aware push:** Push shows requested application, IP, and device info
- **Rate limiting:** Limit push notifications per user per hour

---

## 10. Directory Services

### LDAP — Lightweight Directory Access Protocol

**Overview:** Directory access protocol based on X.500 DAP standard; uses TCP port 389 (LDAP) or 636 (LDAPS/TLS).

**Directory structure:** Hierarchical (tree-based); Entries organized in a Directory Information Tree (DIT)

**LDAP distinguished name (DN) structure:**

```
DN: cn=alice.chen,ou=Users,ou=Engineering,dc=company,dc=com

Attributes:
  cn    = Common Name (alice.chen)
  ou    = Organizational Unit (Users, Engineering)
  dc    = Domain Component (company, com)
  uid   = User ID
  sn    = Surname
  mail  = Email address
  memberOf = Group memberships
```

**LDAP operations:**
- **Bind:** Authenticate to the directory
- **Search:** Query for entries matching criteria
- **Add:** Create a new entry
- **Modify:** Change attributes of an entry
- **Delete:** Remove an entry
- **Compare:** Test if an entry has a specific attribute value
- **Modrdn:** Move or rename an entry
- **Abandon:** Abandon an outstanding operation

**LDAP authentication methods:**
- **Simple bind (anonymous):** No authentication; read-only access to public info
- **Simple bind (authenticated):** Username + plaintext password (use only over LDAPS)
- **SASL bind:** Uses SASL mechanisms (Kerberos, DIGEST-MD5, EXTERNAL for client certs)

**Security:** Use LDAPS (LDAP over TLS, port 636) or StartTLS upgrade to encrypt bind credentials. Plain LDAP transmits credentials in clear text.

### Active Directory (AD)

**Overview:** Microsoft's implementation of LDAP-based directory services with Kerberos authentication, Group Policy, and extensive Windows ecosystem integration.

**Key AD components:**

| Component | Description |
|-----------|------------|
| **Domain** | Administrative boundary; shares security policy and directory database |
| **Forest** | Collection of one or more domains with a shared schema and global catalog |
| **Domain Controller (DC)** | Server hosting AD DS; stores directory database (NTDS.dit) |
| **Global Catalog (GC)** | Partial attribute replica of all forest objects; enables cross-domain queries |
| **Organizational Unit (OU)** | Container for organizing objects within a domain; target for Group Policy |
| **Group Policy Object (GPO)** | Policy settings applied to OUs, sites, or domain |
| **SYSVOL** | Shared folder on DCs containing GPOs and scripts; replicated via DFSR |
| **FSMO Roles** | 5 Flexible Single Master Operations roles (PDC Emulator, RID Master, Infrastructure Master, Schema Master, Domain Naming Master) |

**AD object types:**
- Users (inetOrgPerson)
- Computers
- Groups (Security, Distribution; Domain Local, Global, Universal)
- Service accounts and Managed Service Accounts (MSAs, gMSAs)
- Organizational Units (OUs)
- Group Policy Objects (GPOs)

**AD security features:**
- Fine-Grained Password Policies (PSOs): different password policies for different user groups
- Protected Users security group: enforces strict authentication (Kerberos only, no NTLM, no credential caching)
- Credential Guard: protects LSASS credentials using Hyper-V isolation
- LAPS (Local Administrator Password Solution): automatic, unique local admin passwords per device

### RADIUS — Remote Authentication Dial-In User Service

**Overview:** AAA protocol for network access authentication (RFC 2865). Originally for dial-up; now used for VPN, WiFi (802.1X), and network device authentication.

**Port:** UDP 1812 (authentication/authorization), UDP 1813 (accounting) — legacy: 1645/1646

**RADIUS components:**
- **RADIUS Client (NAS):** Network Access Server — VPN gateway, WiFi access point, switch
- **RADIUS Server:** Authenticates users; returns Access-Accept or Access-Reject with optional attributes
- **RADIUS Proxy:** Forwards requests to appropriate RADIUS server (used in federation)
- **User directory:** LDAP/AD, local file, or database that RADIUS queries

**RADIUS authentication flow (PAP — insecure, illustrative):**

```
1. User connects to VPN / WiFi
2. NAS → RADIUS Server: Access-Request (username, password XOR'd with shared secret, NAS-IP, NAS-Port)
3. RADIUS Server: Authenticates against directory; evaluates policy
4. RADIUS Server → NAS: Access-Accept (with attributes: VLAN, IP pool, idle timeout)
   OR Access-Reject (with reply message)
   OR Access-Challenge (prompt for additional info — MFA OTP)
5. NAS: Grants or denies access per RADIUS decision
```

**RADIUS accounting:**
- NAS sends Accounting-Start when session begins (includes session ID, username, NAS info)
- Interim updates sent periodically (data transferred, session duration)
- Accounting-Stop sent when session ends (total data, reason for disconnect)

**RADIUS limitations:**
- Shared secret between NAS and RADIUS server — if compromised, authentication can be intercepted
- Only the password field is obfuscated (not the entire packet)
- UDP-based (less reliable than TCP; RADIUS/TLS addresses this)
- No per-command authorization (see TACACS+)

### TACACS+ — Terminal Access Controller Access Control System Plus

**Overview:** Cisco-developed protocol for AAA of network devices (routers, switches, firewalls). Separates authentication, authorization, and accounting into distinct functions.

**Port:** TCP 49

**TACACS+ vs. RADIUS key differences:**

| Feature | TACACS+ | RADIUS |
|---------|---------|--------|
| Transport | TCP | UDP |
| Encryption | Encrypts entire body | Encrypts password field only |
| AAA separation | Separate A/A/A processes | Combined A/A |
| Per-command authorization | Yes — authorize each command | No — all or nothing |
| Vendor | Cisco-originated | IETF standard |
| Best for | Network device admin | Network access (VPN, WiFi) |

**TACACS+ per-command authorization:**

This is TACACS+'s most important differentiator. When an admin runs a command on a router, the device checks with TACACS+ whether that specific command (with those specific arguments) is authorized for that user:

```
Admin types: "configure terminal" on router
Router → TACACS+ Server: "Is admin alice allowed to run 'configure terminal'?"
TACACS+ Server: Check policy for alice in admin group
TACACS+ Server → Router: PERMIT
Router: Allows command execution; logs authorization record
```

This enables fine-grained role separation: read-only NOC staff can run show commands but not configure commands; network engineers can configure interfaces but not create new users; only network admins can make routing protocol changes.

---

## 11. Biometrics Deep Dive

### Biometric System Components

1. **Sensor/Capture device:** Captures the biometric sample (fingerprint scanner, camera, microphone)
2. **Feature extraction:** Processes the raw sample into a mathematical template (minutiae points, iris codes)
3. **Template storage:** Stores the enrolled template securely (on device, server, or smart card)
4. **Matcher:** Compares live sample template against stored template; produces similarity score
5. **Decision engine:** Compares similarity score against threshold; outputs match/non-match

### Biometric Error Rates

**False Acceptance Rate (FAR) / False Match Rate (FMR):**
- Probability that the system incorrectly accepts an unauthorized person
- Security error — an impostor is authenticated
- Lower is better from a security perspective

**False Rejection Rate (FRR) / False Non-Match Rate (FNMR):**
- Probability that the system incorrectly rejects an authorized person
- Usability error — a legitimate user is denied access
- Lower is better from a usability perspective

**Crossover Error Rate (CER) / Equal Error Rate (EER):**
- The threshold point at which FAR = FRR
- Lower CER = more accurate biometric system
- Used to compare biometric system accuracy across vendors
- Typical values: FAR 0.001% and FRR 0.1% for high-quality fingerprint systems

**FAR/FRR tradeoff:**
```
Threshold → Strict (high)   → Low FAR (secure)  + High FRR (inconvenient)
Threshold → Lenient (low)   → High FAR (insecure) + Low FRR (convenient)

CER is where FAR == FRR — the optimal balance point
```

**Example decision:**
- Banking application: Set threshold closer to strict (low FAR); reject more legitimate users to prevent unauthorized access
- Physical access for convenience: Set threshold closer to lenient (low FRR); accept more impostors to avoid frustrating authorized employees

### Biometric Attack Types

| Attack | Description | Mitigation |
|--------|------------|-----------|
| **Spoofing (presentation attack)** | Fake fingerprint, photo/video of face, recorded voice | Liveness detection (3D face, capacitive fingerprint, voice challenge) |
| **Replay attack** | Replay of captured biometric data | Challenge-response liveness; freshness tokens |
| **Template manipulation** | Modify stored templates to accept impostor | Secure template storage; template encryption; integrity checks |
| **Enrollment fraud** | Enroll impostor's biometric under legitimate identity | In-person enrollment with ID verification |
| **Template reconstruction** | Reverse-engineer biometric from template (especially iris) | Cancelable biometrics (transform template; can be re-rolled if compromised) |

---

## 12. IAM in Cloud Environments

### Cloud IAM Concepts

Cloud platforms implement IAM differently from on-premises AD environments. Key concepts:

**AWS IAM:**
- **Users:** Individual IAM accounts (best practice: use only for programmatic access; use SSO for humans)
- **Roles:** Collections of policies; assumed by users, services, or external accounts; temporary credentials via STS
- **Policies:** JSON documents specifying allow/deny for specific actions on specific resources
- **Principal:** Who makes the request (user, role, service)
- **Effect:** Allow or Deny
- **Action:** The API call (e.g., s3:GetObject, ec2:StartInstances)
- **Resource:** The ARN of the target (e.g., arn:aws:s3:::my-bucket/*)
- **Condition:** Additional constraints (MFA required, IP range, time of day)

**AWS IAM policy example:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::company-data-bucket/*",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "StringEquals": {"aws:RequestedRegion": "us-east-1"}
      }
    }
  ]
}
```

**AWS Role assumption:**
- Humans authenticate via IdP (Okta/AzureAD) → receive SAML assertion → AWS STS converts to temporary role credentials
- Services (EC2, Lambda) use instance profiles/execution roles — no static credentials stored
- Cross-account access via role trust policies

**Azure AD / Entra ID:**
- Conditional Access: policy-based access control combining identity, device, location, risk into access decisions
- Privileged Identity Management (PIM): JIT role activation with time limits and approval workflows
- Managed Identities: Azure-native service identity; eliminates need for stored credentials

### Federated Identity for Cloud

**SCIM provisioning:**
- IdP (Okta, Azure AD) automatically provisions/deprovisions users in cloud apps
- When user is terminated in IdP, SCIM deactivates them in all connected apps automatically
- Eliminates manual deprovisioning across dozens of SaaS applications

**Workforce Identity Federation (WIF):**
- Allows external identities (contractors, partner organizations) to access cloud resources using their existing IdP credentials
- No long-lived credentials stored in the cloud
- AWS: IAM Identity Center, Web Identity Federation, STS AssumeRoleWithWebIdentity
- GCP: Workload Identity Federation, Workforce Identity Federation

---

## 13. Key Terms Quick Reference

| Term | Definition |
|------|-----------|
| AAA | Authentication, Authorization, Accounting |
| ABAC | Attribute-Based Access Control — policy-based on subject/object/environment attributes |
| ACL | Access Control List — list of subjects and their permissions on an object |
| Authentication | Proving claimed identity |
| Authorization | Determining what an authenticated identity may do |
| CER / EER | Crossover/Equal Error Rate — where FAR equals FRR in biometrics |
| CTAP2 | Client to Authenticator Protocol 2 — part of FIDO2 standard |
| DAC | Discretionary Access Control — owner-controlled ACLs |
| DSD | Dynamic Separation of Duty — cannot activate conflicting roles in same session |
| FAR | False Acceptance Rate — biometric: impostor incorrectly accepted |
| FIDO2 | Fast IDentity Online 2 — phishing-resistant passwordless authentication standard |
| FRR | False Rejection Rate — biometric: authorized user incorrectly rejected |
| JIT | Just-in-Time — on-demand, time-limited privilege grant |
| KDC | Key Distribution Center — Kerberos trusted third party |
| LDAP | Lightweight Directory Access Protocol — X.500-based directory access protocol |
| MAC | Mandatory Access Control — system-enforced labels and clearances |
| MFA | Multi-Factor Authentication — two or more factors from different categories |
| OIDC | OpenID Connect — authentication layer on top of OAuth 2.0 |
| PAM | Privileged Access Management — controls and audits privileged account use |
| PASM | Privileged Account and Session Management — traditional PAM with vaulting and session recording |
| PEDM | Privilege Elevation and Delegation Management — controls what privileged commands users can run |
| PDP | Policy Decision Point — evaluates access policy and returns permit/deny |
| PEP | Policy Enforcement Point — enforces the PDP's access decision |
| PIP | Policy Information Point — provides attributes to PDP |
| RBAC | Role-Based Access Control — permissions tied to roles; users assigned to roles |
| SAML | Security Assertion Markup Language — XML-based federated identity protocol |
| SCIM | System for Cross-domain Identity Management — automated provisioning protocol |
| SoD | Separation of Duties — no single person controls an entire sensitive process |
| SSO | Single Sign-On — authenticate once, access many applications |
| SSD | Static Separation of Duty — mutually exclusive role assignments |
| TACACS+ | Terminal Access Controller Access Control System Plus — AAA for network devices; per-command authorization |
| TGT | Ticket Granting Ticket — Kerberos proof of authentication; used to request service tickets |
| WebAuthn | Web Authentication API — W3C standard; part of FIDO2 |
| ZTNA | Zero Trust Network Access — application-specific access without network-level trust |

---

*Domain 5 cross-references: Domain 1 (access control policy and governance); Domain 3 (cryptographic foundations of authentication protocols, PKI for certificates); Domain 6 (access recertification audits, authentication configuration testing); Domain 7 (account monitoring, SOC detection of unauthorized access attempts).*

*Last updated: 2026-03-01 | Reference: CISSP CBK (ISC)², NIST SP 800-63B, NIST SP 800-207, RFC 6749 (OAuth 2.0), W3C WebAuthn, FIDO Alliance*
