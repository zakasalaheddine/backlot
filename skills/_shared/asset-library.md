# The asset library — on-disk conventions

Human-inspectable, versioned, referenced by ID. Both output skills read from here;
never inline a throwaway identity.

```
assets/
├── characters/<char-id>/
│   ├── character.json
│   └── refs/*.png
└── products/<product-id>/
    ├── product.json
    └── refs/*.png
```

IDs are auto-assigned as `slug-NN` (e.g. `maya-01`, `heart-mug-01`) unless you pass
an explicit `--id`. The whole library is managed by `scripts/assets.py` — you never
hand-write these files.

## character.json
```json
{
  "id": "maya-01",
  "name": "Maya",
  "persona": "mid-20s, warm, girl-next-door, casual-chic, soft makeup",
  "appearance": {
    "descriptor": "canonical text description injected into every prompt",
    "wardrobe_default": "oversized cream knit, gold hoops",
    "negative": "no heavy makeup, no tattoos, no sunglasses"
  },
  "refs": ["refs/ref_00.png", "refs/ref_01.png", "refs/ref_02.png", "refs/ref_03.png"],
  "seed_prompt": "prompt used to originate her",
  "created_from": "generate | upload",
  "voice": {
    "provider": "elevenlabs",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "name": "Rachel",
    "settings": { "stability": 0.5, "similarity_boost": 0.75 }
  },
  "version": 1
}
```

`voice` is optional until locked (`assets.py set-voice`) — but once a character
speaks in any video, lock it: the voice is as much her identity as the face refs.
Every VO take then uses it via `audio_gen.py tts --character maya-01`.

## product.json
```json
{
  "id": "heart-mug-01",
  "name": "Personalized Heart Mug",
  "descriptor": "white ceramic mug, printed photo + name on front",
  "refs": ["refs/upload_00.png", "refs/upload_01.png"],
  "constraints": "print area must stay legible and undistorted; keep true white"
}
```

## Commands you'll use
```bash
python scripts/assets.py list                       # what exists
python scripts/assets.py get   --id maya-01          # full manifest + abs ref paths
python scripts/assets.py refs  --id maya-01          # just the ref paths
python scripts/assets.py originate-character ...      # generate a turnaround
python scripts/assets.py ingest-character  ...        # lock from real photos
python scripts/assets.py create-product    ...        # lock a product from photos
```

## Storage note
Local `assets/` in-repo for v0 (simple, inspectable; contents are gitignored).
Manifests store **relative** ref paths, so moving to object storage later (S3/R2
with URL refs) is a manifest change, not a rewrite. Keep it URL-agnostic.
