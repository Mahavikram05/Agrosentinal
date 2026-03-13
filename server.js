import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import multer from 'multer';
import { v2 as cloudinary } from 'cloudinary';
import { createClient } from '@supabase/supabase-js';
import Anthropic from '@anthropic-ai/sdk';

dotenv.config();

// ── Init ──────────────────────────────────────────────────────────────────────
const app = express();

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key:    process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
});

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const upload = multer({ storage: multer.memoryStorage() });

// ── Middleware ──────────────────────sss──────────────────────────────────────────
app.use(cors({
  origin: [
    'http://localhost:3000',s
    'http://localhost:3001',
    process.env.FRONTEND_URL || 'https://your-app.vercel.app'
  ]
}));
app.use(express.json({ limit: '10mb' }));

// ── Health Check ──────────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'AGRO SENTINEL AI Backend' });
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'AGRO SENTINEL AI Backend', version: '2.0.0' });
});

// ── Scan Plant Image ──────────────────────────────────────────────────────────
app.post('/api/scan', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: 'No image uploaded' });

    // 1. Upload to Cloudinary
    const uploadResult = await new Promise((resolve, reject) => {
      const stream = cloudinary.uploader.upload_stream(
        { folder: 'plant-scans' },
        (error, result) => error ? reject(error) : resolve(result)
      );
      stream.end(req.file.buffer);
    });

    console.log('✅ Uploaded to Cloudinary:', uploadResult.secure_url);

    // 2. Analyze with Claude
    const base64Image = req.file.buffer.toString('base64');
    const claudeRes = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1000,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: {
              type: 'base64',
              media_type: req.file.mimetype,
              data: base64Image
            }
          },
          {
            type: 'text',
            text: `You are an expert plant pathologist. Analyze this plant image.
Reply ONLY with this exact JSON, no extra text, no markdown:
{
  "species": "common plant name",
  "scientific_name": "scientific name",
  "disease": "disease name or healthy",
  "severity": "none or mild or moderate or severe",
  "confidence": 90,
  "care_tips": ["tip1", "tip2", "tip3"]
}`
          }
        ]
      }]
    });

    // 3. Parse Claude response
    const raw = claudeRes.content[0].text;
    const analysis = JSON.parse(raw.replace(/```json|```/g, '').trim());
    console.log('✅ Claude analysis:', analysis);

    // 4. Save to Supabase
    const { data, error } = await supabase
      .from('scans')
      .insert({
        uploaded_image_url: uploadResult.secure_url,
        claude_result: analysis,
        species: analysis.species,
        disease: analysis.disease,
        severity: analysis.severity,
      })
      .select()
      .single();

    if (error) throw error;
    console.log('✅ Saved to Supabase, scan ID:', data.id);

    res.json({
      success: true,
      image_url: uploadResult.secure_url,
      analysis,
      scan_id: data.id
    });

  } catch (err) {
    console.error('❌ Error:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── Get All Scans ─────────────────────────────────────────────────────────────
app.get('/api/scans', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('scans')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) throw error;
    res.json({ success: true, scans: data });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── Start Server ──────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`🚀 AGRO SENTINEL AI running on http://localhost:${PORT}`);
});