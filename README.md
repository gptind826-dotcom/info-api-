# 🌐 IP Geolocation API

A powerful, production-ready IP geolocation API that provides detailed information about any IP address or domain name. Built with Flask, MaxMind GeoLite2 database, and ip-api.com fallback.

## 👑 Owner

**𝐄𝐗𝐔〆𝐏𝐑𝐈𝐌𝐄**

- **Telegram Channel:** [https://t.me/exucodex](https://t.me/exucodex)
- **API Live Demo:** [https://info-api-g8j7.onrender.com](https://info-api-g8j7.onrender.com)

---

## ✨ Features

- ✅ **Dual Input Support** - Works with both IP addresses and domain names
- ✅ **Database First** - Fast local lookups using MaxMind GeoLite2
- ✅ **Smart Fallback** - Auto-fills missing data from ip-api.com
- ✅ **Anycast Detection** - Identifies common anycast IPs (Google DNS, Cloudflare, etc.)
- ✅ **Reverse DNS** - Automatically resolves hostnames
- ✅ **Caching** - 24-hour caching for optimal performance
- ✅ **Production Ready** - Deployed on Render with auto-scaling

---

## 📊 API Response Format

```json
{
  "ip": "8.8.8.8",
  "hostname": "dns.google",
  "city": "Mountain View",
  "region": "CA",
  "country": "US",
  "loc": "37.4056,-122.0775",
  "org": "AS15169 Google LLC",
  "postal": "94043",
  "timezone": "America/Los_Angeles",
  "telegram": "https://t.me/exucodex",
  "anycast": true
}
