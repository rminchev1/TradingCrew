# App Icons

Place your application icons in this directory for the Electron builds.

## Required Icons

### macOS (.icns)
- **File**: `icon.icns`
- **Size**: 1024x1024px base image
- **Tool**: Use `png2icns` or online converter to create from PNG

### Windows (.ico)
- **File**: `icon.ico`
- **Sizes**: Multiple sizes embedded (16, 32, 48, 64, 128, 256)
- **Tool**: Use ImageMagick or online converter

### Linux (.png)
- **File**: `icon.png`
- **Size**: 512x512px or 1024x1024px PNG with transparency

## Creating Icons

### Quick Method (Online):
1. Create a 1024x1024px PNG logo
2. Visit https://www.electronjs.org/docs/latest/tutorial/icon-generation
3. Use tools like:
   - https://cloudconvert.com/png-to-icns (macOS)
   - https://convertico.com/ (Windows)
   - Keep original PNG for Linux

### Using ImageMagick (All Platforms):
```bash
# Install ImageMagick
brew install imagemagick  # macOS
sudo apt install imagemagick  # Linux

# Convert PNG to ICO (Windows)
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico

# For macOS ICNS, use png2icns:
npm install -g png2icns
png2icns icon.icns icon.png
```

## Design Recommendations

- Use a square canvas (1024x1024px)
- Keep important elements centered
- Use transparency for rounded corners
- Ensure icon is recognizable at small sizes (16x16)
- Test icon on both light and dark backgrounds

## Temporary Icon

The app currently uses a placeholder circular icon with chart lines. Replace these files with your custom TradingCrew logo once designed.
