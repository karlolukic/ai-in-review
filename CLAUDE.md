# Project Instructions for Claude

This file contains developer instructions for maintaining and updating the LLM Timeline Visualization.

## Adding Future Years

When Simon publishes his year-in-review post (typically late December):

### 1. Run the scraper

```bash
# Using uv (recommended)
uv sync
uv run python scrape_year_in_llms.py 2026

# Or using pip
pip install -r requirements.txt
python scrape_year_in_llms.py 2026
```

### 2. Update the visualization

The codebase uses dynamic year constants, so adding a new year is minimal:

1. Add the new year's data to `timelineData` in `index.html`:
   ```javascript
   2026: {
       source: "https://simonwillison.net/2026/Dec/31/...",
       title: "The 2026 title",
       events: [...],
       themes: [...]
   }
   ```

2. That's it - all buttons, filters, charts, and header links auto-update from `timelineData`.

### Expected URL Pattern

Simon's posts typically follow:
```
simonwillison.net/YYYY/Dec/31/[slug]/
```

Common slugs: `the-year-in-llms`, `llms-in-YYYY`, `ai-in-YYYY`

## Deployment

### Netlify (Current)

The site is deployed at https://ai-in-review.netlify.app

To redeploy after changes:
```bash
netlify deploy --prod --dir=.
```

Or push to GitHub and Netlify will auto-deploy if connected.

### Manual Netlify CLI Setup

```bash
npm install -g netlify-cli
netlify login
netlify sites:create --name ai-in-review --account-slug karlolukic
netlify deploy --prod --dir=.
```

### GitHub Pages Alternative

1. Go to Settings → Pages
2. Select "Deploy from branch" → main
3. Site will be at `https://username.github.io/ai-in-review`

### Local Development

Just open `index.html` in any browser. No server required.

## Architecture Notes

### Dynamic Year Handling

The code derives years from data rather than hardcoding:

```javascript
const YEARS = Object.keys(timelineData).map(Number).sort();
const LATEST_YEAR = Math.max(...YEARS);
```

All year buttons, filters, and chart ranges use these constants.

### Key Functions

- `createYearFilters()` - Generates year filter buttons for all tabs
- `renderBriefView()` - 30-Second Brief tab
- `renderTimeline()` - D3.js swimlane timeline
- `renderCharts()` - Category trends, company activity, pricing charts
- `renderEventsList()` - Searchable events list

### Categories

- models, tools, concepts, companies, research, pricing

### Impact Scoring

Events are ranked by: category count, link count, numeric mentions, theme mentions.

## Files

```
├── index.html              # Main visualization (HTML/CSS/JS)
├── scrape_year_in_llms.py  # Python scraper for future years
├── pyproject.toml          # Python project config (for uv)
├── requirements.txt        # Python dependencies (pip)
├── netlify.toml            # Netlify deployment config
├── LICENSE                 # MIT License
├── README.md               # User-facing documentation
└── CLAUDE.md               # This file (developer instructions)
```
