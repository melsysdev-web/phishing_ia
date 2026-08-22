# 📦 Microsoft Edge Add-ons Upload Guide

**Version**: 1.0.2 (Updated with UI Redesign)  
**Release Date**: 2026-08-25  
**ZIP File**: `phishing-detector-extension.zip` (30 KB)

---

## 📋 Pre-Upload Checklist

- [x] Extension tested in Chrome (compatible with Edge)
- [x] All animations working smoothly
- [x] Manifest.json updated and valid
- [x] Icons all present (128px, 48px, 16px)
- [x] No console errors
- [x] Security reviewed
- [x] Privacy policy ready

---

## 📦 ZIP Contents

> **El `manifest.json` va en la RAÍZ del ZIP, no dentro de una carpeta.**
> Empaquetar la carpeta `extension/` hace que la tienda responda
> *"Manifest file is missing or unreadable"* y rechace la subida. Genera el
> paquete con `scripts\package_extension.ps1`, que lo valida antes de crearlo.

```
ai-phishing-detector-1.0.0.zip
├── manifest.json  ← en la RAÍZ, no dentro de una carpeta
├── config.js     ← URL y clave del backend; sin él nada arranca
├── background/
│   ├── background.js
│   └── health_check.js
├── content/
│   └── content.js
├── icons/
│   ├── icon128.png
│   ├── icon16.png
│   └── icon48.png
├── options/
│   ├── options.css
│   ├── options.html
│   └── options.js
├── popup/
│   ├── popup.css
│   ├── popup.html
│   └── popup.js
├── services/
│   └── api_client.js
├── sidebar/
│   ├── sidebar.css
│   ├── sidebar.html
│   └── sidebar.js
└── utils/
    └── error_messages.js
```

**Size**: 30 KB (uncompressed: ~150 KB)

---

## 🚀 Step-by-Step Upload Process

### Step 1: Prepare for Upload

1. Go to: https://partner.microsoft.com/en-us/dashboard/microsoftedge/overview
2. Sign in with Microsoft account (or create one)
3. Navigate to: **Publish** → **Extensions**

### Step 2: Create or Update Listing

#### If NEW listing:
```
1. Click "Add a new extension"
2. Fill in:
   Name: AI Phishing Detector
   Category: Safety & Privacy
   Listing language: English (US)
```

#### If UPDATING (recommended):
```
1. Find existing "AI Phishing Detector" listing
2. Click "Edit" or "Update"
3. This page will be your update form
```

### Step 3: Upload Extension Package

```
Section: "Extension packages"
1. Click "Choose file"
2. Select: phishing-detector-extension.zip
3. Wait for validation (usually 1-2 minutes)
   ✅ Should pass validation
   ❌ If errors: see Troubleshooting section
4. System will extract manifest and show info
```

### Step 4: Fill in Extension Details

**Description** (240 characters max):
```
Real-time phishing detection using AI, VirusTotal, Safe Browsing, 
and Fact Check APIs. Analyzes URLs and webpage content with professional 
animations and smooth interactions. Completely free and open-source.
```

**Detailed Description**:
```
## Features

### URL Analysis
- Multi-signal ML pipeline with Random Forest and RoBERTa models
- VirusTotal threat intelligence (malware, phishing)
- Google Safe Browsing (real-time threats)
- Google Fact Check (misinformation detection)
- HTTPS validation and domain age checks
- Smooth animations powered by anime.js

### Content Analysis
- Fake news / real content detection
- RoBERTa-based classification
- Confidence scoring

### User Experience
- Modern flat design interface
- Smooth animations and transitions
- Popup for quick analysis
- Expanded sidebar with detailed results
- History tracking
- Configurable backend URL

### Privacy
- All analysis runs through your configured backend
- No data collection beyond analysis
- Chrome extension: local storage only
- Optional API key configuration
```

### Step 5: Add Screenshots

**Required**: 2-5 screenshots (1280x800 or similar)

Suggested screenshots:
1. **Popup Analysis** - Show popup with gauge and animations
2. **Sidebar Results** - Show sidebar with detailed results
3. **Content Analysis** - Show content classification tab
4. **Score Visualization** - Highlight the ML model scores

**Screenshot Tips**:
- Use high contrast colors
- Show real results (not mockups)
- Include the UI with animations if possible
- Add arrows/annotations if helpful

### Step 6: Privacy & Security

**Privacy Policy URL**:
```
https://github.com/melsysdev-web/phishing_ia/blob/main/PRIVACY_POLICY.md
```

Or create one if doesn't exist (see template below)

**Requested Permissions Justification**:
```
- tabs: Access active tab URL for analysis
- scripting: Extract webpage content for content analysis
- storage: Save configuration and history locally
- activeTab: Analyze current webpage
- alarms: Periodic health checks to backend
```

### Step 7: Version Information

**Version Number**: `1.0.2`

**Release Notes**:
```
## v1.0.2 - UI Redesign & Animation Update (2026-08-25)

### ✨ New Features
- Redesigned UI with flat design aesthetic
- Smooth animations powered by anime.js library
- Improved visual hierarchy and spacing
- Better hover effects and micro-interactions

### 🎬 Animation Updates
- Gauge fill animation (1200ms smooth)
- Staggered cascade for reasons and signals
- Synchronized score bar and counter
- Bounce effects for badges and icons
- Smooth state transitions

### 🐛 Bug Fixes
- Fixed deprecated datetime.utcnow() usage
- Cleaned up unused imports
- Improved performance with will-change hints

### 📊 Performance
- Optimized animations for 60 FPS
- Reduced memory footprint
- Faster content extraction
- Better caching strategy

### 📱 Compatibility
- Full Chrome/Edge Manifest V3 support
- Responsive design
- Works on desktop and tablet

For detailed changelog: https://github.com/melsysdev-web/phishing_ia/blob/main/docs/changelog.md
```

### Step 8: Target Audience

```
Target Audience: Everyone
Age Rating: 3+ (General Audience)
Category: Safety & Privacy
Subcategories:
  - Security
  - Privacy
  - Safety
```

### Step 9: Links & Resources

```
Support Website: https://github.com/melsysdev-web/phishing_ia
Privacy Policy: https://github.com/melsysdev-web/phishing_ia/wiki/Privacy
Help/FAQ: https://github.com/melsysdev-web/phishing_ia/issues
License: MIT
```

### Step 10: Review & Submit

```
1. Review all information
2. Confirm you own/control the extension
3. Accept Microsoft Edge Add-ons terms
4. Click "Submit for review"
5. Receive confirmation email
```

---

## ⏱️ Review Timeline

| Stage | Duration | Status |
|-------|----------|--------|
| Initial validation | 1-2 min | Automatic |
| Malware scan | 5-10 min | Automatic |
| Human review | 24-48 hrs | Manual |
| Approval/Rejection | Immediate | Email notification |
| Publishing | 1-2 hrs | After approval |

---

## ✅ Approval Criteria Checklist

Microsoft will check:

- [x] Manifest v3 compliant
- [x] No malware or malicious code
- [x] Permissions justified and minimal
- [x] Privacy policy present
- [x] Functional screenshots
- [x] Accurate description
- [x] No adult content
- [x] Genuine functionality
- [x] No deceptive practices

**Our extension**:
- ✅ All criteria met
- ✅ Clean code (no malware)
- ✅ Minimal permissions
- ✅ Privacy-first design
- ✅ Real functionality
- ✅ Transparent operation

---

## 🔧 Troubleshooting

### Upload Error: "Invalid manifest"

**Solution**:
```json
Check extension/manifest.json:
- version: "1.0.2"
- manifest_version: 3
- name: "AI Phishing Detector"
- permissions array present
```

### Upload Error: "File too large"

**Current size**: 30 KB  
**Limit**: 500 MB  
**Status**: ✅ Well within limits

### Upload Error: "Unsupported format"

**Solution**:
- El ZIP debe contener el **contenido** de `extension/`, no la carpeta
- `manifest.json` tiene que quedar en la raíz del archivo
- Estructura correcta:
  ```
  ai-phishing-detector-1.0.0.zip
  ├── manifest.json
  ├── config.js
  └── ...
  ```
- Usa `.\scripts\package_extension.ps1`: verifica esto sobre el ZIP ya
  construido y lo borra si el manifest no quedó en la raíz.

### Review Rejection: "Unclear permissions"

**Solution**:
Update manifest.json permissions with clear justification in description

### Review Rejection: "Malware detected"

**Very unlikely** - our code is:
- Open source on GitHub
- No minified/obfuscated code
- Clean dependencies only

**If occurs**:
1. Request manual review
2. Link to GitHub repo for verification
3. Explain anime.js CDN usage (only external dependency)

---

## 📝 Privacy Policy Template

If you need to create one:

```markdown
# Privacy Policy

## Overview
AI Phishing Detector is committed to protecting your privacy.

## Data We Don't Collect
- We do NOT collect or store URLs you analyze
- We do NOT track your browsing
- We do NOT send your data to our servers
- We do NOT use analytics or tracking pixels

## Data We Handle
- URLs are sent to third-party services ONLY at your request:
  - VirusTotal (https://virustotal.com)
  - Google Safe Browsing (https://safebrowsing.google.com)
  - Google Fact Check (https://toolbox.google.com/factcheck)

## Local Storage
- Analysis results cached locally in your browser
- History stored locally (configurable)
- Backend URL configuration stored locally

## Third-Party Services
See their privacy policies:
- VirusTotal: https://virustotal.com/en/privacy/
- Google Safe Browsing: https://www.google.com/policies/privacy/
- Google Fact Check: https://www.google.com/policies/privacy/

## Configuration
- Backend URL: Configured in extension options
- API Key: Optional, stored locally
- No account required

## Open Source
- Code available on GitHub
- Full source code transparency
- Community review welcome

## Questions?
GitHub: https://github.com/melsysdev-web/phishing_ia/issues
```

---

## 📊 After Publishing

### Monitor Performance

Once published:
1. Track install count on Edge dashboard
2. Monitor user ratings and reviews
3. Check for support requests

### Update Process

For future updates:
1. Create new ZIP with updated extension
2. Update version in manifest.json
3. Submit new version on partner dashboard
4. Process repeats (faster for updates)

### Common Update Cycle

```
v1.0.2 - Initial with anime.js redesign (Current)
v1.0.3 - Bug fixes and performance tweaks (Next)
v1.1.0 - Major feature additions (Planned)
```

---

## 🎯 Success Metrics to Track

After publishing:
- [ ] Installation count > 100
- [ ] Average rating > 4.0
- [ ] No critical issues reported
- [ ] CI/CD integration working
- [ ] Regular updates maintained

---

## 📋 Checklist Before Upload

- [x] ZIP file created: `phishing-detector-extension.zip`
- [x] File size: 30 KB (within limits)
- [x] Manifest.json present and valid
- [x] All icons included
- [x] No console errors when tested
- [x] Privacy policy ready
- [x] Screenshots prepared
- [x] Release notes written
- [x] Extension tested on Edge
- [x] Permissions documented

---

## 🚀 Ready to Upload!

Your extension is **ready for Microsoft Edge Add-ons**.

**Next steps**:
1. Go to https://partner.microsoft.com/en-us/dashboard/microsoftedge/overview
2. Sign in / create account
3. Follow upload steps above
4. Submit for review

**Expected outcome**:
✅ Approval within 24-48 hours  
✅ Published to Microsoft Edge Add-ons  
✅ Available to 30M+ Edge users

---

**Need Help?**
- GitHub Issues: https://github.com/melsysdev-web/phishing_ia/issues
- Edge Support: https://support.microsoft.com/en-us/microsoft-edge
- Manifest v3: https://developer.chrome.com/docs/extensions/mv3/

---

**Last Updated**: 2026-08-25  
**Status**: Ready for upload ✅
