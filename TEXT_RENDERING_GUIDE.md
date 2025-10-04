# Text Rendering Guide for AI-Generated Book Covers

## 🎯 Quick Summary

**For text on covers (titles, author names)**: Use **GPT-Image-1** (OpenAI's latest model)

## 📊 Model Comparison

| Model | Text Rendering | Quality | Speed | Cost |
|-------|----------------|---------|-------|------|
| **GPT-Image-1** | ⭐⭐⭐⭐⭐ Excellent | Very High | Medium | Higher |
| **DALL-E 3** | ⭐⭐ Poor | High | Fast | Medium |
| **Imagen** | ❌ None | High | Fast | Lower |

## ✅ Best Practice for Cover Images

### Step 1: Set Your Default Backend
Go to **Settings → Image Generation** and select:
- **GPT-Image-1** (RECOMMENDED for covers with text)

### Step 2: Structure Your Prompt
Separate visual description from text requirements:

```
[VISUAL SCENE DESCRIPTION]
A whimsical children's book cover showing...

TEXT REQUIREMENTS (CRITICAL):
- At TOP CENTER: "Book Title" in elegant, large, legible font
- At BOTTOM: "Written by Author Name" in clear, readable font
- Text must be CRISP and PROMINENT
- Use contrasting colors for readability
```

### Step 3: Key Phrases for Better Text
Include these words in your text section:
- **LEGIBLE** / **READABLE** / **CLEAR**
- **CRISP** / **SHARP** / **PROMINENT**
- **LARGE** / **BOLD** (for emphasis)
- Specify **EXACT** placement (TOP CENTER, BOTTOM, etc.)
- Mention **CONTRAST** (white text on dark background, etc.)

## ⚠️ Common Mistakes

### ❌ Don't Do This:
```
"A cover with the title 'Book Name' and author 'Author Name' somewhere on it"
```
**Problem**: Too vague, text placement and style unclear

### ✅ Do This Instead:
```
TEXT REQUIREMENTS (CRITICAL):
- At the TOP CENTER: Display "Book Name" in large, elegant, clearly readable serif font
- At the BOTTOM: Display "by Author Name" in smaller but crisp, legible sans-serif font
- Both text elements must be WHITE with subtle shadow for contrast against the blue background
```
**Why Better**: Specific placement, style, size, and contrast instructions

## 🔄 If Text Still Doesn't Appear

### Option 1: Regenerate Multiple Times
GPT-Image-1 sometimes needs 2-3 attempts to get text right

### Option 2: Simplify Text Requirements
- Use shorter titles if possible
- Reduce the number of text elements
- Increase font size requirements

### Option 3: Post-Process with Image Editor
- Generate the scene without text
- Add text in Photoshop/GIMP/Canva afterward
- This gives you perfect control over typography

## 🎨 Example Prompts

### Good Prompt (High Success Rate):
```
A magical forest scene with glowing mushrooms and friendly woodland creatures.

TEXT REQUIREMENTS (CRITICAL):
- TOP CENTER: "The Magic Forest" in large, whimsical, clearly legible font with white color
- BOTTOM: "by Jane Smith" in smaller, clean, readable font with white color
- Ensure HIGH CONTRAST against the dark forest background
```

### Better Prompt (Very High Success Rate):
```
SCENE: Enchanted forest with bioluminescent mushrooms, friendly rabbits and foxes, starry night sky

TEXT PLACEMENT:
1. TITLE at TOP: "The Magic Forest"
   - Font: Large, whimsical, decorative but LEGIBLE
   - Color: Bright white with subtle glow
   - Size: Prominent, taking up 20% of top area
   
2. AUTHOR at BOTTOM: "by Jane Smith"
   - Font: Clean, simple, READABLE sans-serif
   - Color: White
   - Size: Smaller but clearly visible

CRITICAL: All text must be CRISP, SHARP, and fully LEGIBLE
```

## 💡 Pro Tips

1. **Be Specific About Placement**: "top center", "bottom left", "centered"
2. **Describe Font Style**: "elegant script", "playful rounded", "classic serif"
3. **Specify Colors**: Helps ensure readability
4. **Emphasize Legibility**: Use words like CLEAR, CRISP, READABLE
5. **Test Multiple Times**: First generation might not be perfect

## 🔧 Current Settings

You can check/change your settings at:
**https://8002-i5roi2rdc6qph6bf3vt6m-6532622b.e2b.dev/settings**

Current recommendation: **GPT-Image-1** ✅

## 📚 Resources

- [OpenAI GPT-Image-1 Documentation](https://platform.openai.com/docs/guides/images)
- Your Settings Page: `/settings` → "Image Generation" tab
