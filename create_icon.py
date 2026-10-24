from PIL import Image, ImageDraw

# Create a 256x256 image with smooth anti-aliased icon
size = (256, 256)
img = Image.new("RGBA", size, (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Dark glowing rounded rectangle background
padding = 16
radius = 48
bg_color = (18, 18, 22, 240)
draw.rounded_rectangle([padding, padding, 256 - padding, 256 - padding], radius=radius, fill=bg_color, outline=(30, 215, 96, 200), width=6)

# Spotify Green Music Note & Translation lines
# Draw soundwave / lyrics lines
green = (30, 215, 96, 255)
white = (255, 255, 255, 240)

# Line 1 (Original lyric line)
draw.rounded_rectangle([50, 70, 206, 90], radius=10, fill=white)

# Line 2 (Translated lyric line in Spotify Green)
draw.rounded_rectangle([50, 110, 180, 126], radius=8, fill=green)

# Line 3 (Original lyric line)
draw.rounded_rectangle([50, 146, 206, 166], radius=10, fill=white)

# Line 4 (Translated lyric line in Spotify Green)
draw.rounded_rectangle([50, 186, 160, 202], radius=8, fill=green)

# Save multi-size .ico
img.save(r"C:\pw\spotify-lyrics\icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Icon generated successfully!")
