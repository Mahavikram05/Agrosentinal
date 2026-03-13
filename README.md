# 🌿 AGRO SENTINEL AI — Backend

An AI-powered plant disease detection and species identification backend built with Node.js, Express, Claude AI, Cloudinary, and Supabase.

---

## 🚀 Tech Stack

| Technology | Purpose |
|---|---|
| Node.js + Express | Backend server |
| Claude AI (Anthropic) | Plant analysis via AI |
| Cloudinary | Image storage |
| Supabase (PostgreSQL) | Database for scan history |
| Multer | Image upload handling |

---

## 📁 Project Structure

```
agrosential-backend/
├── server.js          # Main server file
├── .env               # Environment variables (never commit this!)
├── package.json       # Project dependencies
└── node_modules/      # Installed packages
```

---

## ⚙️ Setup Instructions

### 1. Clone or open the project
```bash
cd agrosential-backend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Create `.env` file
Create a file named `.env` in the root folder and add:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

FRONTEND_URL=http://localhost:3000
PORT=4000
```

### 4. Set up Supabase Database
Run this SQL in your Supabase SQL Editor:

```sql
CREATE TABLE plants (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  common_name TEXT NOT NULL,
  scientific_name TEXT,
  image_url TEXT,
  category TEXT CHECK (category IN ('disease', 'species', 'both')),
  disease_name TEXT,
  tags TEXT[],
  source TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE scans (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT,
  uploaded_image_url TEXT,
  claude_result JSONB,
  species TEXT,
  disease TEXT,
  severity TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

### 5. Start the server

**Development (auto-restarts on file changes):**
```bash
npm run dev
```

**Production:**
```bash
npm start
```

Server runs on: `http://localhost:4000`

---

## 📡 API Endpoints

### Health Check
```
GET /
GET /api/health
```
Returns server status.

---

### Scan a Plant Image
```
POST /api/scan
Content-Type: multipart/form-data
Body: image (file)
```

**Response:**
```json
{
  "success": true,
  "image_url": "https://res.cloudinary.com/...",
  "analysis": {
    "species": "Tomato",
    "scientific_name": "Solanum lycopersicum",
    "disease": "Early Blight",
    "severity": "moderate",
    "confidence": 92,
    "care_tips": [
      "Remove infected leaves immediately",
      "Apply fungicide every 7 days",
      "Avoid overhead watering"
    ]
  },
  "scan_id": "uuid-here"
}
```

---

### Get All Past Scans
```
GET /api/scans
```

**Response:**
```json
{
  "success": true,
  "scans": [...]
}
```

---

## 🔗 Connecting Frontend

In your Next.js frontend, create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:4000
```

Then call the API:
```ts
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/scan`, {
  method: 'POST',
  body: formData
});
```

---

## 🌐 Deployment

### Deploy Backend to Render
1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set build command: `npm install`
5. Set start command: `npm start`
6. Add all `.env` variables in Render's Environment tab
7. Deploy → get your live URL

### Deploy Frontend to Vercel
1. Push Next.js code to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project
3. Connect your GitHub repo
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
5. Deploy

---

## 🔑 Where to Get API Keys

| Key | Where to get |
|---|---|
| `SUPABASE_URL` + `SUPABASE_KEY` | supabase.com → Project Settings → API |
| `CLOUDINARY_*` | cloudinary.com → Dashboard |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |

---

## ⚠️ Important Security Notes

- Never commit your `.env` file to GitHub
- Add `.env` to your `.gitignore`
- Reset any API keys you accidentally share publicly
- Use environment variables in production (Render, Vercel)

---

## 📞 Support

For issues, check:
1. All `.env` values are filled correctly
2. Supabase tables are created
3. Backend is running on port 4000
4. Frontend `.env.local` points to correct backend URL
