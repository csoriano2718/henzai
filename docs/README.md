# henzai Website

This directory contains the GitHub Pages website for henzai.

## 🌐 Live Site

The website is automatically deployed to GitHub Pages at:
**https://csoriano2718.github.io/henzai/**

## 📝 Development

The website is a single-page application built with:
- Pure HTML/CSS (no build step required)
- Inter font from Google Fonts
- Responsive design
- Clean, modern aesthetic inspired by Perplexity

## 🎥 Adding Demo Videos/Images

To add demo media:

1. Add your video/image files to this `docs/` directory
2. Update the `<div class="demo-media">` sections in `index.html`
3. Replace the placeholder with:
   ```html
   <video autoplay loop muted playsinline>
       <source src="your-video.mp4" type="video/mp4">
   </video>
   ```
   or
   ```html
   <img src="your-image.png" alt="Demo description">
   ```

## 🚀 Deployment

GitHub Pages automatically deploys from the `docs/` folder on the `main` branch.
Any push to `main` will update the live site within a few minutes.

## 🎨 Customization

All styling is in the `<style>` section of `index.html`. Key variables:
- `--primary`: Main brand color (#3584e4)
- `--text-primary`: Primary text color
- `--text-secondary`: Secondary text color
- `--background`: Page background
- `--surface`: Card/surface background

## 📦 Structure

- Hero section with CTA
- Demo section (4 feature demos)
- Features grid (6 key features)
- Installation instructions
- Footer with links

