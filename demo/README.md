# Domino Boneyard API Demo

This is a simple web-based demonstration of the [Domino Boneyard API](https://github.com/bantoinese83/Domino-Boneyard-API). It shows how to interact with the API using JavaScript to create domino sets, draw tiles, and display them with their images.

## Features

- Create new domino sets
- Draw tiles with images
- Shuffle the boneyard
- View API responses in real-time

## How to Use

1. Open the demo page
2. Click "Create New Domino Set" to initialize a domino set
3. Click "Draw 7 Tiles" to draw tiles from the boneyard
4. Click "Shuffle Tiles" to return all tiles to the boneyard and shuffle them

## Setting Up on GitHub Pages

To host this demo on GitHub Pages:

1. Create a new repository (e.g., `domino-boneyard-demo`)
2. Upload these demo files to the repository
3. Go to repository Settings → Pages
4. Under "Source", select "main" branch
5. Click Save
6. Your site will be published at `https://yourusername.github.io/domino-boneyard-demo/`

## Development

If you want to modify this demo:

1. Clone the repository
2. Make your changes to `index.html`
3. Test locally by opening the HTML file in a browser
4. Commit and push your changes

## API Integration

This demo shows how to integrate with the following Domino Boneyard API endpoints:

- `POST /api/set/new` - Create a new domino set
- `POST /api/set/{set_id}/draw` - Draw tiles from the boneyard
- `POST /api/set/{set_id}/shuffle` - Shuffle tiles

For more endpoints and functionality, see the [full API documentation](https://domino-boneyard-api.onrender.com/docs). 